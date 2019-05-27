/* Example definition of a simple mode that understands a subset of
 * TSL:
 */

CodeMirror.defineSimpleMode("tsl", {
  // The start state contains the rules that are intially used
  start: [
    // The regex matches the token, the token property contains the type
    {regex: /"(?:[^\\]|\\.)*?(?:"|$)/, token: "string"},
    // You can match multiple tokens at once. Note that the captured
    // groups must span the whole string in this case
    {regex: /(bash|be|calculate|change|combine|count|empty|extract|find|for|log|remember|remove|replace|reverse|run|save|select|sort|split|take|unique|write)(\s+)(.*)/,
     token: ["keyword", null, "variable-2"]},
    // Rules are matched in the order in which they appear, so there is
    // no ambiguity between this one and the one above
    {regex: /(?:bash|be|calculate|change|combine|count|empty|extract|find|for|log|remember|remove|replace|reverse|run|save|select|sort|split|take|unique|write)\b/,
     token: "keyword"},
    {regex: /every|all|other|odd|even|none/, token: "atom"},
    {regex: /(zero|null|n?one|two|three|four|five|six|seven|eight|nine|ten|dozen)|((but-la|fir|la)st|(2|seco)nd|(3|thi)rd|(\d+|four|fif|six|seven|eig|nine|ten)th|last)|[-+]?(?:\.\d+|\d+\.?\d*)/i,
     token: "number"},
    {regex: /^\s*#.*/, token: "comment"},
    {regex: /\/(?:[^\\]|\\.)*?\//, token: "variable-3"},
    // A next property will cause the mode to move to a different state
    {regex: /\/\*/, token: "comment", next: "comment"},
    {regex: /[-+\/*=<>!]+/, token: "operator"},
    // indent and dedent properties guide autoindentation
    {regex: /[\{\[\(]/, indent: true},
    {regex: /[\}\]\)]/, dedent: true},
    {regex: /^\s*for\s+/, indent: true},
    {regex: /^\s*---|repeat\b/, dedent: true},
    {regex: /\[[^]]+\]/, token: "variable"},
    // You can embed other modes with the mode property. This rule
    // causes all code between << and >> to be highlighted with the XML
    // mode.
    {regex: /<</, token: "meta", mode: {spec: "xml", end: />>/}}
  ],
  // The multi-line comment state.
  comment: [
    {regex: /.*?\*\//, token: "comment", next: "start"},
    {regex: /.*/, token: "comment"}
  ],
  // The meta property contains global information about the mode. It
  // can contain properties like lineComment, which are supported by
  // all modes, and also directives like dontIndentStates, which are
  // specific to simple modes.
  meta: {
    dontIndentStates: ["comment"],
    lineComment: "//"
  }
});
