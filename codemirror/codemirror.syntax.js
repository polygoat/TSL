CodeMirror.defineSimpleMode("tsl", {
  start: [
    {regex: /"(?:[^\\]|\\.)*?(?:"|$)/, token: "string"},
    {regex: /\[[\w.\-–=\d\s!%$§&()#+×*~|£ƒ€<>°öäüß²³@áâàåãæéêíïîìôòøûùÿçñªº¿]+\]/i, token: "string"},
    {regex: /\s*(add|bash|be|calculate|change|combine|count|empty|extract|find|for|in|log|remember|remove|replace|repeat|\-{3}|reverse|run|save|select|sort|split|take|unique|write)\s*/i, sol: true,
     token: "keyword"},
    {regex: /(?<=\s|^)(every|all|other|odd|even|none)(?=\s|$)/i, token: "number"},
    {regex: /(line|file|folder|result|dot|period|tab|colon|semi\-?colon|space)s?(?=\s|$)/, token: "string"},
    {regex: /(?<=\s|^)(zero|null|n?one|two|three|four|five|six|seven|eight|nine|ten|dozen)(?=\s|$)/,
     token: "number"},
    {regex: /\b(but-last|first|last|(2|seco)nd|(3|thi)rd|(\d+|four|fif|six|seven|eig|nine|ten)th|last)(?=\s|$)/, token: "number"},
    {regex: /(\s|^)[-+]?(?:\.\d+|\d+\.?\d*)(\s|$)/, token: "number"},
    {regex: /\s*#.*/, token: "comment", sol: true},
    {regex: /[-+\/*=<>!]+/, token: "operator"},
    {regex: /[\{\[\(]/, indent: true},
    {regex: /[\}\]\)]/, dedent: true},
    {regex: /\s*for\s+/, indent: true, sol: true},
    {regex: /\s*\-{3}|repeat\b/, dedent: true, sol: true},
    {regex: /(?<=\s|^)(in|as|from|to|until|with|by|of|without|where|between)(?=\s|$)/, token: "variable-2"}
  ], 
  meta: {
    dontIndentStates: ["comment"],
    lineComment: "#"
  }
});