function scribble_emojis(_string, _sprite, _lookup) {
	var _scribble = scribble(_string).preprocessor(__injected_emoji_preprocessor)
	_scribble.__userPreprocessorFunc = undefined;
	
	_scribble.__emojiSprite = _sprite;
	_scribble.__emojiLookup = _lookup;
	
	_scribble.preprocessor = function(_function) {
        if (_function != __userPreprocessorFunc)
        {
            if ((_function != undefined) && (not script_exists(_function)))
            {
                __scribble_error("Preprocessor functions must be stored in scripts in global scope");
            }
            
            __model_cache_name_dirty = true;
            __userPreprocessorFunc = _function;
        }
        
        return self;
    }
	return _scribble;
}



/// @ignore
function __injected_emoji_preprocessor(_string="") {
	if (__userPreprocessorFunc = undefined) {
		// Feather disable once GM1021
		_string = __userPreprocessorFunc(_string)
	}
	_string = __scribble_preparse_buffered(_string, __emojiSprite, __emojiLookup);
	return _string;
}


