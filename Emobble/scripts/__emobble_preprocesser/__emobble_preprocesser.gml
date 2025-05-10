// Give a literal reference to the font and bullet point sprite so they are included in the compile.
// There is a pending Pull request for Scribble currently by Tabularelf which will resolve the need for this
// https://github.com/JujuAdams/Scribble/pull/613
var scribble_include_in_compile_fnt = scribble_fallback_font;
var scribble_include_in_compile_spr = scribble_fallback_bulletpoint;

function __emobble_preprocesser(_string) {
	_string = scribblify_emojis(_string, EMOBBLE_ATLAS_SPRITE, EMOBBLE_ATLAS_LOOKUP)
	return _string;
}

//This will set the default preprocessor scribble uses to convert emojis for you.
scribble_default_preprocessor_set(__emobble_preprocesser);