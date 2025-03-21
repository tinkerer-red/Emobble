function __scribble_preparse_buffered(_text, _sprite, _lookup) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);
    
    if (string_length(_text) == 0) return "";
	
    var _sprite_name = sprite_get_name(_sprite);
    var byte_len = string_byte_length(_text);
	
    // Write input buffer
    buffer_write(input_buff, buffer_text, _text);
    buffer_seek(input_buff, buffer_seek_start, 0);
	
    while (buffer_tell(input_buff) < byte_len) {
        parse_emoji_chain(input_buff, output_buff, _lookup, _sprite_name, byte_len);
    }
	
    buffer_seek(output_buff, buffer_seek_start, 0);
    var parsed_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";
	
    buffer_resize(input_buff, 0);
    buffer_resize(output_buff, 0);
	
    return parsed_str;
}

function parse_emoji_chain(_input_buff, _output_buff, _lookup, _sprite_name, _byte_len) {
	static emoji_buffer = buffer_create(0, buffer_grow, 1); // Static buffer for emoji sequences
    
	var _prev_codepoint = 0;
	var _codepoint = 0;
	
	while (buffer_tell(_input_buff) < _byte_len) {
		_codepoint = buffer_read_codepoint(_input_buff);
		
		while (is_emoji_codepoint(_codepoint)) {
			// Handle Variation Selector (\uFE0F)
	        if (_codepoint == 0xFE0F && buffer_get_size(emoji_buffer) == 0) {
				// Mofidy previous codepoint and convert it into an emoji
				if (_prev_codepoint) {
					buffer_write_codepoint(emoji_buffer, _prev_codepoint);
					_prev_codepoint = 0;
				}
				buffer_write_codepoint(emoji_buffer, _codepoint);
				_codepoint = 0;
				break;
	        }
			
			// Push the codepoint into the buffer
			if (_codepoint) {
	            buffer_write_codepoint(emoji_buffer, _codepoint);
	            _codepoint = buffer_read_codepoint(_input_buff);
			}
		}
		
		// write the previous codepoint
		if (_prev_codepoint) {
			buffer_write_codepoint(_output_buff, _prev_codepoint);
		}
		
		// Write the emoji sequence from the buffer
        if (buffer_get_size(emoji_buffer)) {
			__attempt_to_write_emoji(emoji_buffer, _output_buff, _lookup, _sprite_name);
            buffer_resize(emoji_buffer, 0); // Clear buffer for next sequence
        }
		
		_prev_codepoint = _codepoint;
	}
	
	//write the final codepoint
	if (_prev_codepoint) {
		buffer_write_codepoint(_output_buff, _prev_codepoint);
	}
	
	//buffer_resize(emoji_buffer, 0); // Reset the buffer
}

/// @ignore
function __attempt_to_write_emoji(_emoji_buffer, _output_buff, _lookup, _sprite_name) {
    // Convert buffer to lookup key
	buffer_seek(_emoji_buffer, buffer_seek_start, 0);
    var sequence_key = buffer_read(_emoji_buffer, buffer_text);
	
	// Lookup by full sequence first
    var _sprite_index = _lookup[$ sequence_key];
    if (_sprite_index != undefined) {
        buffer_write(_output_buff, buffer_text, $"[{_sprite_name},{_sprite_index},0]");
        return;
    }
	
    // Check if `\uFE0F` exists and remove it if necessary
	static stripped_buffer = buffer_create(0, buffer_grow, 1);
	buffer_seek(_emoji_buffer, buffer_seek_start, 0);
    while (buffer_tell(_emoji_buffer) < buffer_get_size(_emoji_buffer)) {
        var codepoint = buffer_read_codepoint(_emoji_buffer);
        if (codepoint != 0xFE0F) {
            buffer_write_codepoint(stripped_buffer, codepoint);
        }
    }
	
    // Try again with the sequence without `\uFE0F`
    if (buffer_tell(stripped_buffer)) {
		buffer_seek(stripped_buffer, buffer_seek_start, 0);
		var stripped_key = buffer_read(stripped_buffer, buffer_text);
        var _sprite_index = _lookup[$ stripped_key];

        if (_sprite_index != undefined) {
            buffer_write(_output_buff, buffer_text, $"[{_sprite_name},{_sprite_index},0]");
            buffer_resize(stripped_buffer, 0)
            return;
        }
    }
	
    buffer_resize(stripped_buffer, 0)
	
    // If sequence is not found, write individual emojis
    buffer_seek(_emoji_buffer, buffer_seek_start, 0);
    while (buffer_tell(_emoji_buffer) < buffer_get_size(_emoji_buffer)) {
		var codepoint = buffer_read_codepoint(_emoji_buffer);
		if (codepoint == 0) return;
		if (codepoint == 0xFE0F) continue;
		
		var _sprite_index = _lookup[$ codepoint];
		
        if (_sprite_index != undefined) {
            buffer_write(_output_buff, buffer_text, $"[{_sprite_name},{_sprite_index},0]");
        }
		else {
            buffer_write_codepoint(_output_buff, codepoint); // Write normal text if no emoji variant
        }
    }
}

function is_emoji_codepoint(_codepoint) {
    return (
        (_codepoint >= 0x1F300 && _codepoint <= 0x1F9FF) || // Standard emoji range
        (_codepoint >= 0x2600 && _codepoint <= 0x26FF) ||   // Misc symbols that can be emoji
        (_codepoint == 0x200D) || // Zero Width Joiner
        (_codepoint == 0xFE0F)    // Variation Selector
    );
}

function buffer_read_codepoint(_buff) {
    var byte1 = buffer_read(_buff, buffer_u8);
	
	// 1-byte (ASCII)
    if (byte1 < 0x80) {
        return byte1;
    } 
	// 2-byte UTF-8
    else if ((byte1 & 0xE0) == 0xC0) {
        return ((byte1 & 0x1F) << 6)
				| (buffer_read(_buff, buffer_u8) & 0x3F);
    } 
	// 3-byte UTF-8
    else if ((byte1 & 0xF0) == 0xE0) {
        return ((byte1 & 0x0F) << 12)
				| ((buffer_read(_buff, buffer_u8) & 0x3F) << 6)
				| (buffer_read(_buff, buffer_u8) & 0x3F);
    } 
    // 4-byte UTF-8
	else if ((byte1 & 0xF8) == 0xF0) {
        return ((byte1 & 0x07) << 18)
				| ((buffer_read(_buff, buffer_u8) & 0x3F) << 12)
				| ((buffer_read(_buff, buffer_u8) & 0x3F) << 6)
				| (buffer_read(_buff, buffer_u8) & 0x3F);
    }

    return 0; // Invalid sequence
}

function buffer_write_codepoint(_buffer, _codepoint) {
    if (_codepoint <= 0x7F) {
        buffer_write(_buffer, buffer_u8, _codepoint);
    }
    else if (_codepoint <= 0x7FF) {
        buffer_write(_buffer, buffer_u8, 0xC0 | (_codepoint >> 6));
        buffer_write(_buffer, buffer_u8, 0x80 | (_codepoint & 0x3F));
    }
    else if (_codepoint <= 0xFFFF) {
        buffer_write(_buffer, buffer_u8, 0xE0 | (_codepoint >> 12));
        buffer_write(_buffer, buffer_u8, 0x80 | ((_codepoint >> 6) & 0x3F));
        buffer_write(_buffer, buffer_u8, 0x80 | (_codepoint & 0x3F));
    }
    else {
        buffer_write(_buffer, buffer_u8, 0xF0 | (_codepoint >> 18));
        buffer_write(_buffer, buffer_u8, 0x80 | ((_codepoint >> 12) & 0x3F));
        buffer_write(_buffer, buffer_u8, 0x80 | ((_codepoint >> 6) & 0x3F));
        buffer_write(_buffer, buffer_u8, 0x80 | (_codepoint & 0x3F));
    }
}

function CacheSystem() constructor {
	data = {};
	static __string_hash = {} //explicetly used to improve the speed at which we hash strings
	static save = function(_value) {
		var _data = data;
		
		var _cache_ref_key_count = argument_count;
		var _last_index = _cache_ref_key_count-1;
		
		for(var _i=1; _i<_cache_ref_key_count; _i++) {
			var _arg = argument[_i];
			
			//hash the argument
			var _hash = hash_input(_arg);
			
			//parse the cache for matches
			var _temp = struct_get_from_hash(_data, _hash)
			if (_temp != undefined) {
				_data = _temp;
				if (_i == _last_index) {
					//keep the data from being overritten by arbitrary chance
					var _value_holder_static = static_get(_data)
					_value_holder_static.value = _value;
				}
			}
			else { //if no match is found make a new one
				if (_i == _last_index) {
					var _value_holder = {};
					
					//keep the data from being overritten by arbitrary chance
					var _value_holder_static = {value: _value};
					static_set(_value_holder, _value_holder_static)
					
					struct_set_from_hash(_data, _hash, _value_holder);
				}
				else {
					var _new_data = {};
					struct_set_from_hash(_data, _hash, _new_data);
					_data = _new_data;
				}
			}
		}
	}
	static load = function() {
		var _data = data;
		
		var _cache_ref_key_count = argument_count;
		var _last_index = _cache_ref_key_count-1;
		
		for(var _i=0; _i<_cache_ref_key_count; _i++) {
			var _arg = argument[_i];
			
			//hash the argument
			var _hash = hash_input(_arg);
			
			//parse the cache for matches
			var _temp = struct_get_from_hash(_data, _hash)
			if (_temp != undefined) {
				_data = _temp
			}
			else { //if no match is found make a new one
				return undefined;
			}
		}
		
		var _static = static_get(_data)
		if (_static) return _static[$ "value"]; // will be undefined if it's not there
		
		return undefined;
	}
	static remove = function() {
		var _prev_data = undefined;
		var _data = data;
		
		var _cache_ref_key_count = argument_count;
		var _last_index = _cache_ref_key_count-1;
		
		for(var _i=0; _i<_cache_ref_key_count; _i++) {
			var _arg = argument[_i];
			
			//hash the argument
			var _hash = hash_input(_arg);
			
			var _temp = struct_get_from_hash(_data, _hash)
			//parse the cache for matches
			var _temp = struct_get_from_hash(_data, _hash)
			if (_temp != undefined) {
				_prev_data = _data;
				_data = _temp;
			}
			else { //if no match is found make a new one
				return;
			}
		}
		
		if (_prev_data) {
			struct_remove_from_hash(_prev_data, _hash)
		}
		
		return;
	}
	static flush = function() {
		data = {};
		__string_hash = {};
	}
	// Hashing
	static hash_input = function(_arg) {
		var _hash = 2166136261; // FNV-1a 32-bit offset basis
		
	    switch (typeof(_arg)) {
	        case "number": case "int32": case "int64": case "bool": {
	            return hash_combine(_hash, _arg);
	        }
	        case "string": {
	            var _sting_hash = __string_hash[$ _arg]
				if (_sting_hash == undefined) {
					var _len = string_length(_arg);
		            for (var i = 1; i <= _len; i++) {
		                _hash = hash_combine(_hash, ord(string_char_at(_arg, i)));
		            }
					__string_hash[$ _arg] = _hash;
				}
				else {
					_hash = _sting_hash;
				}
				
	            return _hash;
	        }
	        case "array": {
	            var _len = array_length(_arg);
	            for (var i = 0; i < _len; i++) {
	                _hash = hash_combine(_hash, hash_input(_arg[i]));
	            }
	            return _hash;
	        }
	        case "struct": {
	            var _keys = variable_struct_get_names(_arg);
	            array_sort(_keys, true); // Ensure deterministic order
	            var _len = array_length(_keys);
	            for (var i = 0; i < _len; i++) {
	                var _key = _keys[i];
	                var _val = variable_struct_get(_arg, _key);
	                _hash = hash_combine(_hash, hash_input(_key));
	                _hash = hash_combine(_hash, hash_input(_val));
	            }
	            return _hash;
	        }
	        case "method": case "ptr": case "ref": {
				return hash_combine(_hash, hash_input(string(_arg)));
	        }
	        case "undefined": {
	            return hash_combine(_hash, 0xBADF00D); // Arbitrary constant
	        }
	        case "null": {
	            return hash_combine(_hash, 0xDEADBEEF); // Arbitrary constant
	        }
	        default: {
	            return hash_combine(_hash, hash_input(string(_arg))); // Fallback to string representation
	        }
	    }
	}
    static hash_combine = function(_h, _value) {
        _value = _value & 0xFFFFFFFF; // Ensure 32-bit range
        _h = ((_h ^ _value) * 31) & 0xFFFFFFFF; // Prime multiplication
        return ((_h << 5) | (_h >> 27)) & 0xFFFFFFFF; // Rotate bits for better mixing
    };
}

//show_debug_message(__scribble_preparse_buffered("Hello 😊 World", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Good job 👍🏽 Buddy", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Family 👨‍👩‍👧‍👦 Day", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Heart ❤️ Check", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Star ★ vs ✩", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Fire 🔥 Emoji", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Wave 👋🏾 Test", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Person 🚶‍♀️ Walking", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("⚠️ Warning Label", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Moon 🌕 vs 🌑", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Snowman ☃️ Test", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Email ✉️ Check", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Check ✔️ or ❌", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Numbers ➀ ➁ ➂", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Scissors ✂️ Cut", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Invisible 🤺 Man", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Kiss 💋 Mark", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Arrow ⬆️⬇️⬅️➡️", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Dagger 🗡️ Test", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Superhero 🦸‍♂️ Power", fntTwitterTwemoji_Lite_16));

//// 🛠 Edge Cases & Stress Testing

//// ✅ Incorrectly formatted start (special characters)
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("@#$% 😊 Test", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("!123 ❤️ Numbers", fntTwitterTwemoji_Lite_16));

//// ✅ Incorrectly formatted end (junk characters)
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("End of Test 😎 %^&*", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Final ✅ 123!!!", fntTwitterTwemoji_Lite_16));

//// ✅ Unicode + Emoji Mix
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("漢字 ❤️ Test", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("¡Hola! 👋🏽 ¿Cómo estás?", fntTwitterTwemoji_Lite_16));

//// ✅ Special ASCII Sequences
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("ASCII Test *^_^* ☺️", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("Emoticon :) converted? 😃", fntTwitterTwemoji_Lite_16));

//// ✅ Emoji Sequences with Extra Spaces
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("    Extra Space 😊 Test    ", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("👨‍👩‍👦‍👦     Family with space", fntTwitterTwemoji_Lite_16));

//// ✅ Unicode Control Characters
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("Test\u200BHidden Zero Width Space", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("🚀 Rocket\u202ETest Right-To-Left", fntTwitterTwemoji_Lite_16));

//// ✅ Overloaded Emojis & Symbols
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("🔴🔵⚫⚪🔺🔻🔸🔹🔶🔷 Stars & Shapes", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("♠️♥️♣️♦️ Cards", fntTwitterTwemoji_Lite_16));

//// ✅ Broken / Partial Emoji Data
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("🚀 Rocket \u1F680 Broken", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("\u200D\u200D Zero Width Joiners", fntTwitterTwemoji_Lite_16));

//// ✅ Double Emojis Stacked
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("🎵🎶 Music Notes Together", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("💡💬 Ideas & Chat", fntTwitterTwemoji_Lite_16));

//// ✅ Extreme Edge Case: Long Mixed Emoji String
//show_debug_message("")
//show_debug_message(__scribble_preparse_buffered("🤔🤷‍♂️💭 Thinking... 🤔🤷‍♂️💭", fntTwitterTwemoji_Lite_16));
//show_debug_message(__scribble_preparse_buffered("👩‍🚀👨‍🚀🧑‍🚀 Astronaut Crew 👩‍🚀👨‍🚀🧑‍🚀", fntTwitterTwemoji_Lite_16));


///@ignore
function __scribble_noto_mono_preparse(_str) {
	switch (EMOJI_SIZE) {
		case 16: return __scribble_preparse_buffered(_str, fntFontNotoemojiMedium_Lite_16);
		case 24: return __scribble_preparse_buffered(_str, fntFontNotoemojiMedium_Lite_24);
		case 32: return __scribble_preparse_buffered(_str, fntFontNotoemojiMedium_Lite_32);
		case 48: return __scribble_preparse_buffered(_str, fntFontNotoemojiMedium_Lite_48);
		case 64: return __scribble_preparse_buffered(_str, fntFontNotoemojiMedium_Lite_64);
	}
}
function scribble_google_mono(_string) {
	return scribble(_string).preprocessor(__scribble_noto_mono_preparse);
}
function scribble_noto_mono(_string) {
	return scribble(_string).preprocessor(__scribble_noto_mono_preparse);
}

///@ignore
function __scribble_noto_preparse(_str) {
	switch (EMOJI_SIZE) {
		case 16: return __scribble_preparse_buffered(_str, fntGoogleNoto_Lite_16);
		case 24: return __scribble_preparse_buffered(_str, fntGoogleNoto_Lite_24);
		case 32: return __scribble_preparse_buffered(_str, fntGoogleNoto_Lite_32);
		case 48: return __scribble_preparse_buffered(_str, fntGoogleNoto_Lite_48);
		case 64: return __scribble_preparse_buffered(_str, fntGoogleNoto_Lite_64);
	}
}
function scribble_google(_string) {
	return scribble(_string).preprocessor(__scribble_noto_preparse);
}
function scribble_noto(_string) {
	return scribble(_string).preprocessor(__scribble_noto_preparse);
}

///@ignore
function __scribble_segoe_ui_mono_preparse(_str) {
	switch (EMOJI_SIZE) {
		case 16: return __scribble_preparse_buffered(_str, fntFontSeguiemj_Lite_16);
		case 24: return __scribble_preparse_buffered(_str, fntFontSeguiemj_Lite_24);
		case 32: return __scribble_preparse_buffered(_str, fntFontSeguiemj_Lite_32);
		case 48: return __scribble_preparse_buffered(_str, fntFontSeguiemj_Lite_48);
		case 64: return __scribble_preparse_buffered(_str, fntFontSeguiemj_Lite_64);
	}
}
function scribble_microsoft_mono(_string) {
	return scribble(_string).preprocessor(__scribble_segoe_ui_mono_preparse);
}
function scribble_segoe_ui_mono(_string) {
	return scribble(_string).preprocessor(__scribble_segoe_ui_mono_preparse);
}

///@ignore
function __scribble_segoe_ui_preparse(_str) {
	switch (EMOJI_SIZE) {
		case 16: return __scribble_preparse_buffered(_str, fntMicrosoftSegoeUiEmoji_Lite_16);
		case 24: return __scribble_preparse_buffered(_str, fntMicrosoftSegoeUiEmoji_Lite_24);
		case 32: return __scribble_preparse_buffered(_str, fntMicrosoftSegoeUiEmoji_Lite_32);
		case 48: return __scribble_preparse_buffered(_str, fntMicrosoftSegoeUiEmoji_Lite_48);
		case 64: return __scribble_preparse_buffered(_str, fntMicrosoftSegoeUiEmoji_Lite_64);
	}
}
function scribble_microsoft(_string) {
	return scribble(_string).preprocessor(__scribble_segoe_ui_preparse);
}
function scribble_segoe_ui(_string) {
	return scribble(_string).preprocessor(__scribble_segoe_ui_preparse);
}

///@ignore
function __scribble_openmoji_preparse(_str) {
	switch (EMOJI_SIZE) {
		case 16: return __scribble_preparse_buffered(_str, fntOpenmoji_Lite_16);
		case 24: return __scribble_preparse_buffered(_str, fntOpenmoji_Lite_24);
		case 32: return __scribble_preparse_buffered(_str, fntOpenmoji_Lite_32);
		case 48: return __scribble_preparse_buffered(_str, fntOpenmoji_Lite_48);
		case 64: return __scribble_preparse_buffered(_str, fntOpenmoji_Lite_64);
	}
}
function scribble_openmoji(_string) {
	return scribble(_string).preprocessor(__scribble_openmoji_preparse);
}

///@ignore
function __scribble_twemoji_preparse(_str) {
	switch (EMOJI_SIZE) {
		case 16: return __scribble_preparse_buffered(_str, fntTwitterTwemoji_Lite_16);
		case 24: return __scribble_preparse_buffered(_str, fntTwitterTwemoji_Lite_24);
		case 32: return __scribble_preparse_buffered(_str, fntTwitterTwemoji_Lite_32);
		case 48: return __scribble_preparse_buffered(_str, fntTwitterTwemoji_Lite_48);
		case 64: return __scribble_preparse_buffered(_str, fntTwitterTwemoji_Lite_64);
	}
}
function scribble_twemoji(_string) {
	return scribble(_string).preprocessor(__scribble_twemoji_preparse);
}
function scribble_twitter(_string) {
	return scribble(_string).preprocessor(__scribble_twemoji_preparse);
}
function scribble_discord(_string) {
	return scribble(_string).preprocessor(__scribble_twemoji_preparse);
}

///@ignore
function __scribble_whatsapp_preparse(_str) {
	switch (EMOJI_SIZE) {
		case 16: return __scribble_preparse_buffered(_str, fntWhatsapp_Lite_16);
		case 24: return __scribble_preparse_buffered(_str, fntWhatsapp_Lite_24);
		case 32: return __scribble_preparse_buffered(_str, fntWhatsapp_Lite_32);
		case 48: return __scribble_preparse_buffered(_str, fntWhatsapp_Lite_48);
		case 64: return __scribble_preparse_buffered(_str, fntWhatsapp_Lite_64);
	}
}
function scribble_whatsapp(_string) {
	return scribble(_string).preprocessor(__scribble_whatsapp_preparse);
}




