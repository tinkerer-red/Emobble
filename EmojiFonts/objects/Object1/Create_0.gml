/// @description Insert description here
// You can write your code in this editor
yy = 0

var _arr = string_split(get_emojis(), "\n", true)

emoji_str = get_emojis()
string_lines = string_split(emoji_str, "\n", true)

var glyph_strings = [];
var unicode_strings = [];
var name_strings = [];

//need to report a bug to scribble about needing to do this
var _length =(__SCRIBBLE_MAX_LINES-4)/2
for(var _i=0; _i < _length; _i++) {
	var _str = string_lines[_i];
	_str = string_replace_all(_str, @'" :: "', "|");
	_str = string_replace_all(_str, @'"', "");
	var _arr = string_split(_str, "|")
	glyph_strings[_i] = _arr[0];
	unicode_strings[_i] = " :: " + _arr[1] + " :: " + _arr[2];
	//name_strings[_i] = _arr[2];
}

//array_resize(glyph_strings, __SCRIBBLE_MAX_LINES-10)
//array_resize(unicode_strings, __SCRIBBLE_MAX_LINES)
//array_resize(name_strings, __SCRIBBLE_MAX_LINES)

glyph_string = string_join_ext("\n", glyph_strings);
unicode_string = string_join_ext("\n", unicode_strings);
//name_string = string_join_ext("\n", name_strings);

show_debug_overlay(true)

emoji_strings = []
emoji_strings[0] = scribblify_emojis(glyph_string, __emj_emojidex_deluxe_16, __emoji_lookup_emojidex_deluxe())
emoji_strings[1] = scribblify_emojis(glyph_string, __emj_fluent3d_deluxe_16, __emoji_lookup_fluent3d_deluxe())
emoji_strings[2] = scribblify_emojis(glyph_string, __emj_fluentFlat_deluxe_16, __emoji_lookup_fluentFlat_deluxe())
emoji_strings[3] = scribblify_emojis(glyph_string, __emj_icons8_deluxe_16, __emoji_lookup_icons8_deluxe())
emoji_strings[4] = scribblify_emojis(glyph_string, __emj_noto_deluxe_16, __emoji_lookup_noto_deluxe())
emoji_strings[5] = scribblify_emojis(glyph_string, __emj_notoMono_deluxe_16, __emoji_lookup_notoMono_deluxe())
emoji_strings[6] = scribblify_emojis(glyph_string, __emj_openmoji_deluxe_16, __emoji_lookup_openmoji_deluxe())
emoji_strings[7] = scribblify_emojis(glyph_string, __emj_segoeUi_deluxe_16, __emoji_lookup_segoeUi_deluxe())
emoji_strings[8] = scribblify_emojis(glyph_string, __emj_segoeMono_deluxe_16, __emoji_lookup_segoeMono_deluxe())
emoji_strings[9] = scribblify_emojis(glyph_string, __emj_twemoji_deluxe_16, __emoji_lookup_twemoji_deluxe())
