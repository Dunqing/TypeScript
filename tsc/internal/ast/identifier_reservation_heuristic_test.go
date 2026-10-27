package ast_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/microsoft/TypeScript/tsc/internal/ast"
	"github.com/microsoft/TypeScript/tsc/internal/core"
	"github.com/microsoft/TypeScript/tsc/internal/parser"
	"github.com/microsoft/TypeScript/tsc/internal/testutil/parsetestutil"
	"github.com/microsoft/TypeScript/tsc/internal/tspath"
)

func reservationHeuristicPrefix() string {
	var source strings.Builder
	for i := range 65 {
		fmt.Fprintf(&source, "let __heuristic%d;", i)
	}
	return source.String()
}

func reservationHeuristicArray(distinct int) string {
	var source strings.Builder
	source.WriteString("const values=[")
	for i := range 128 {
		fmt.Fprintf(&source, "%q,", fmt.Sprintf("ordinary value %d", i%distinct))
	}
	source.WriteString("];")
	return source.String()
}

func TestIdentifierReservationHeuristic(t *testing.T) {
	t.Parallel()
	prefix := reservationHeuristicPrefix()
	for _, test := range []struct {
		name, source, query string
		want                bool
	}{
		{"empty", "", "probe", false},
		{"small file", `const values=["ordinary value"];`, "ordinary value", true},
		{"repeated value", reservationHeuristicArray(1), "ordinary value 0", true},
		{"eight original keys", reservationHeuristicArray(7), "ordinary value 0", true},
		{"nine original keys", reservationHeuristicArray(8), "ordinary value 0", false},
		{"many distinct values", reservationHeuristicArray(64), "ordinary value 0", false},
		{"node budget", strings.Repeat(";", 300) + reservationHeuristicArray(8), "ordinary value 0", true},
		{"identifier", prefix + `const actualName=0;`, "actualName", true},
		{"private identifier", prefix + `class C { #actualName; }`, "#actualName", true},
		{"quoted property", prefix + `const obj={"propertyName":0};`, "propertyName", true},
		{"computed property", prefix + `const obj={["computedName"]:0};`, "computedName", true},
		{"element access", prefix + `obj["accessName"];`, "accessName", true},
		{"literal type", prefix + `type T="ordinary type value";`, "ordinary type value", false},
	} {
		t.Run(test.name, func(t *testing.T) {
			t.Parallel()
			file := parsetestutil.ParseTypeScript(test.source, false)
			parsetestutil.CheckDiagnostics(t, file)
			if got := file.HasIdentifier(test.query); got != test.want {
				t.Errorf("HasIdentifier(%q) = %v, want %v", test.query, got, test.want)
			}
		})
	}
}

func TestIdentifierReservationJSDocHeuristic(t *testing.T) {
	t.Parallel()
	name := tspath.RootedFilePathFromNormalized("/heuristic.js")
	source := `/** @import { Value } from "./types" */` + reservationHeuristicPrefix() + `const value="ordinary value";`
	file := parser.ParseSourceFile(ast.SourceFileParseOptions{FileName: name, PathKey: tspath.CaseSensitive.PathKey(tspath.RootedPath(name))}, source, core.ScriptKindJS)
	parsetestutil.CheckDiagnostics(t, file)
	if !file.HasIdentifier("./types") {
		t.Error("reparsed JSDoc module name was lost")
	}
	if file.HasIdentifier("ordinary value") {
		t.Error("probe did not filter the ordinary value")
	}
}
