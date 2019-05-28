CodeMirror.defineSimpleMode("tsl", {
  start: [
    {regex: /"(?:[^\\]|\\.)*?(?:"|$)/, token: "string"},
    {regex: /\[[^\]\^]+\]/, token: "string"},
    {regex: /\s*(bash|be|calculate|change|combine|count|empty|extract|find|for|in|log|remember|remove|replace|repeat|\-{3}|reverse|run|save|select|sort|split|take|unique|write)\s*/, sol: true,
     token: "keyword"},
    {regex: /\b(every|all|other|odd|even|none)\b/, token: "number"},
    {regex: /\b(zero|null|n?one|two|three|four|five|six|seven|eight|nine|ten|dozen)\b/i,
     token: "number"},
    {regex: /\b((but-la|fir|la)st|(2|seco)nd|(3|thi)rd|(\d+|four|fif|six|seven|eig|nine|ten)th|last)|[-+]?(?:\.\d+|\d+\.?\d*)\b/, token: "number"},
    {regex: /\s*#.*/, token: "comment", sol: true},
    {regex: /[-+\/*=<>!]+/, token: "operator"},
    {regex: /[\{\[\(]/, indent: true},
    {regex: /[\}\]\)]/, dedent: true},
    {regex: /\s*for\s+/, indent: true, sol: true},
    {regex: /\s*\-{3}|repeat\b/, dedent: true, sol: true},
    {regex: /(in|as|from|to|until|with|by|of|without|where|between)\s/, token: "variable-2"}
  ], 
  meta: {
    dontIndentStates: ["comment"],
    lineComment: "#"
  }
});