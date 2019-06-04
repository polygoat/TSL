let   id 	= 0;
const fs 	= require('fs');
const glob 	= require('glob');
const path 	= require('path');
const _ 	= require('lodash');
const md 	= require('markdown-it')({
	highlight: (str, lang) => {
		const lines 	= str.split('\n');
		let result 		= '';
		let labelClass 	= '';
		let hasOutput = false;

		if(lang == 'filelist') {
			labelClass = ' class="filelist-tab"';
		}

		if(lines[0][0] === '`' && lines[0][1] === '`' && lines[0][2] != '`') {
			let label = lines[0].slice(2).trim();
			hasOutput = (label == 'output');
			result += `<label${labelClass}><span>${label}</span></label><br/>`;
			lines.shift();
			str = lines.join('\n');
		}
		id++;
		code = encodeURIComponent(str).replace(/\n+$/g, '');

		switch(lang) {
			case 'filelist':
				result += `<iframe id="filelist_${id}" class="filelist" src="filelister/index.html?dir=${code}" frameborder="0"></iframe>`;
				break;

			default:
				result += `<iframe id="example_${id}" class="codemirror" src="codemirror/index.html?id=example_${id}&code=${code}&lang=${lang}" frameborder="0"></iframe>`;
		}

		return result;
	}
});
const HTML = {
	HEAD: '',
	FOOT: ''
};

md.use(require('markdown-it-named-headers'));
md.use(require('markdown-it-container'), 'splitscreen', {
  validate: function(params) {
    return params.trim().match(/^split\-?screen\s*$/);
  },

  render: function (tokens, idx) {
    if (tokens[idx].nesting === 1) {
      return '<div class="grid-x split-screen">\n';
    }
    return '</div>\n';
  }
});

md.block.ruler.push('hr', (state, startLine, endLine, silent) => {
	let marker, len,
		markerStartPos = state.bMarks[startLine] + state.tShift[startLine];
	
	if (markerStartPos + 3 > state.eMarks[startLine]) 
		return false;

	marker = state.src.slice(markerStartPos, markerStartPos+3);

    if (marker !== '---' /* ` */) 	return false;
    if (silent) 					return true;

	len = state.tShift[startLine];
	state.line = startLine+1;

    state.tokens.push({
        type: 'hr',
        content: state.getLines(startLine, state.line, len, true),
        lines: [startLine, state.line],
        level: state.level
    });
    return true;
});

md.renderer.rules.hr = (tokens, idx, options) => {
	return '<hr />\n';
};


function compileDocs(filename) {
	if(filename) {
		filename = filename.split(path.sep).pop();
		filename && console.log('	' + filename + ' changed. Recompiling...');
	}

	HTML.HEAD = fs.readFileSync('source/head.html');
	HTML.FOOT = fs.readFileSync('source/foot.html');

	glob.sync('source/**/*.md').forEach(filename => {
		const dist = filename.replace('source/', 'dist/').replace('.md', '.html');
		const markDown = fs.readFileSync(filename);
		HTML.CONTENT = md.render(markDown.toString()).replace(/\n([^\t])/g, '\n\t$1');
		HTML.CONTENT = HTML.CONTENT.replace(/<code>\s*\[([^\]]+)\]\s*<\/code>/g, '<code class="parameter optional" title="(optional)">$1</code>');
		HTML.CONTENT = HTML.CONTENT.replace(/\\newline/g, '<br>');
		fs.writeFileSync(dist, HTML.HEAD + HTML.CONTENT + HTML.FOOT);
	});
	console.log('	All docs compiled.');
	console.log('	Now running livereload on source folder...');
	console.log('');
}

if(process.argv[2] === 'livereload') {
	const livereload = require('livereload');
	const lrserver = livereload.createServer({
		extraExts: ['md','.md'],
		delay: 1000,
		port: 35730
	}, compileDocs);
	
	lrserver.watch(__dirname + "/source").on('change', compileDocs);
} else {
	const http = require('http');
	const url = require('url');

	const escapeShell = cmd => {
	  return '"'+cmd.replace(/\n/g, '\\n').replace(/(["'$`\\])/g,'\\$1')+'"';
	};

	http.createServer((req, res) => {
		const data = url.parse(req.url);
		let result = '';

	  	res.writeHead(200, { 'Content-Type': 'text/plain', 'Access-Control-Allow-Origin': '*' });

		if(data.search) {
			const params = new url.URLSearchParams(data.search);
			let code = params.get('code');

			if(code) {
				code = code.trim();
				const exec = require('child_process').exec;
				exec('python ../../TSLCLI.py ' + escapeShell(code), { shell: true }, (result, error) => {
					res.write(error || result);
	  				res.end();
				});
			}
		} else {
	  		res.write(result);
	  		res.end();
		}
	}).listen(8080);

	console.log('	TSL server started at port 8080.');
}