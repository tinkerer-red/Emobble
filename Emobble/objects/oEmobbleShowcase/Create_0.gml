/// @description Insert description here
// You can write your code in this editor
//function __emj_lookup_<catagory_slug>_<mode>_<size>
show_debug_overlay(true);

yy = 0

var _arr = string_split(get_emojis(), "\n", true)

emoji_str = get_emojis()
string_lines = string_split(emoji_str, "\n", true)
emoji_str = string_join_ext("\n", string_lines, 0, __SCRIBBLE_MAX_LINES)
//*
var glyph_strings = [];
var unicode_strings = [];
var name_strings = [];

var _length = __SCRIBBLE_MAX_LINES
for(var _i=0; _i < _length; _i++) {
	var _str = string_lines[_i];
	_str = string_replace_all(_str, @'" :: "', "|");
	_str = string_replace_all(_str, @'"', "");
	var _arr = string_split(_str, "|")
	glyph_strings[_i] = _arr[0];
	unicode_strings[_i] = " :: " + _arr[1] + " :: " + _arr[2];
	//name_strings[_i] = _arr[2];
}

glyph_string = string_join_ext("\n", glyph_strings);
unicode_string = string_join_ext("\n", unicode_strings);

show_debug_overlay(true);

emoji_strings = [];
emoji_strings[0] = scribblify_emojis(glyph_string, emj_spr_emojidex_deluxe_16,   emj_lt_emojidex_deluxe_16())
emoji_strings[1] = scribblify_emojis(glyph_string, emj_spr_fluent3d_deluxe_16,   emj_lt_fluent3d_deluxe_16())
emoji_strings[2] = scribblify_emojis(glyph_string, emj_spr_fluentFlat_deluxe_16, emj_lt_fluentFlat_deluxe_16())
emoji_strings[3] = scribblify_emojis(glyph_string, emj_spr_icons8_deluxe_16,	 emj_lt_icons8_deluxe_16())
emoji_strings[4] = scribblify_emojis(glyph_string, emj_spr_noto_deluxe_16,		 emj_lt_noto_deluxe_16())
emoji_strings[5] = scribblify_emojis(glyph_string, emj_spr_openmoji_deluxe_16,	 emj_lt_openmoji_deluxe_16())
emoji_strings[6] = scribblify_emojis(glyph_string, emj_spr_segoeUi_deluxe_16,	 emj_lt_segoeUi_deluxe_16())
emoji_strings[7] = scribblify_emojis(glyph_string, emj_spr_twitter_deluxe_16,	 emj_lt_twitter_deluxe_16())

arrays = []
for (var i=0; i<array_length(emoji_strings); i++){
	arrays[i] = string_split(emoji_strings[i], "\n");
}

// now rejoin the string back into the same lines with the unicode
final_lines = [];

for (var i = 0; i < array_length(arrays[0]); i++) {
	var joined = "";
	for (var j = 0; j < array_length(arrays); j++) {
		//if (j != 0) joined += "|";
		joined += arrays[j][i];
	}
	joined += unicode_strings[i];
	final_lines[i] = joined;
}

final_string = string_join_ext("\n", final_lines)