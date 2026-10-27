//// [tests/cases/compiler/generatedNameAvoidsIdentifierLikeStrings.ts] ////

//// [generatedNameAvoidsIdentifierLikeStrings.ts]
// Strings that look like identifiers may be evaluated as code, so generated
// names must avoid them even when the file contains many other names.
let __pad0, __pad1, __pad2, __pad3, __pad4, __pad5, __pad6, __pad7, __pad8, __pad9;
let __pad10, __pad11, __pad12, __pad13, __pad14, __pad15, __pad16, __pad17, __pad18, __pad19;
declare function getObject(): { value: number } | undefined;
const values = ["ordinary value 1", "ordinary value 2", "./module", "1abc"];
const probeName = "_a";
const value = getObject()?.value;
eval(probeName);


//// [generatedNameAvoidsIdentifierLikeStrings.js]
"use strict";
var _b;
// Strings that look like identifiers may be evaluated as code, so generated
// names must avoid them even when the file contains many other names.
let __pad0, __pad1, __pad2, __pad3, __pad4, __pad5, __pad6, __pad7, __pad8, __pad9;
let __pad10, __pad11, __pad12, __pad13, __pad14, __pad15, __pad16, __pad17, __pad18, __pad19;
const values = ["ordinary value 1", "ordinary value 2", "./module", "1abc"];
const probeName = "_a";
const value = (_b = getObject()) === null || _b === void 0 ? void 0 : _b.value;
eval(probeName);
