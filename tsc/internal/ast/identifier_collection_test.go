package ast_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/microsoft/TypeScript/tsc/internal/testutil/parsetestutil"
)

func TestHasIdentifier(t *testing.T) {
	t.Parallel()
	var padding strings.Builder
	for i := range 65 {
		fmt.Fprintf(&padding, "let __padding%d;", i)
	}
	for _, test := range []struct {
		name, source, query string
		want                bool
	}{
		{"empty", "", "probe", false},
		{"identifier", `const actualName=0;`, "actualName", true},
		{"private identifier", `class C { #actualName; }`, "#actualName", true},
		{"quoted property", `const obj={"propertyName":0};`, "propertyName", true},
		{"computed property", `const obj={["computedName"]:0};`, "computedName", true},
		{"element access", `obj["accessName"];`, "accessName", true},
		{"template literal", "const value=`templateName`;", "templateName", true},
		{"literal type", `type T="typeName";`, "typeName", true},
		{"identifier-shaped value", `eval("_a");`, "_a", true},
		{"identifier-shaped value after padding", padding.String() + `eval("_a");`, "_a", true},
		{"private-name-shaped value", `const value="#privateName";`, "#privateName", true},
		{"dollar and digits", `const value="$value_1";`, "$value_1", true},
		{"non-ASCII", `const value="ünïcode";`, "ünïcode", true},
		{"escaped identifier text", `const value="\\u005fa";`, "\\u005fa", true},
		{"value with spaces", `const value="ordinary value";`, "ordinary value", false},
		{"module specifier", `import "./types";`, "./types", false},
		{"leading digit", `const value="1abc";`, "1abc", false},
		{"empty string", `const value="";`, "", false},
		{"numeric literal", `const value=1;`, "1", false},
		{"bigint literal", `const value=1n;`, "1n", false},
		{"overflowing numeric literal", `const value=1e999;`, "Infinity", true},
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
