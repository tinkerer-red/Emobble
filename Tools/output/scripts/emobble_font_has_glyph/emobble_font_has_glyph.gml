// This is a generated file from `build_gml.py` — do not modify.
function __emobble_font_has_glyph(_font, _chr) {
	static __cache = {};
	
	var _font_name = font_get_name(_font);
	
	var _glyphs = __cache[$ _font_name];
	if (_glyphs == undefined) {
		var _info = font_get_info(_font);
		_glyphs = _info.glyphs;
		__cache[$ _font_name] = _glyphs;
	}
	
	return (_glyphs[$ _chr] != undefined);
}
