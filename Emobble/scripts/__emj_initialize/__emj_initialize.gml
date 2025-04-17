function __emobble_preprocesser(_string) {
	_string = scribblify_emojis(_string, EMOBBLE_ATLAS_SPRITE, EMOBBLE_ATLAS_LOOKUP)
	return _string;
}
scribble_default_preprocessor_set(__emobble_preprocesser);