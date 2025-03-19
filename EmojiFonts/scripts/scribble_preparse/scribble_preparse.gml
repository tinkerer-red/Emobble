//feel free to delete any other sizes and fonts you do not plan on using
#macro EMOJI_SIZE 16 //16, 24, 32, 48, 64 supported


function __scribble_preparse_buffered(_text, _font) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);
    
    if (string_length(_text) == 0) return "";
	
    var _font_tag = "[" + font_get_name(_font) + "]";
    var _font_limited = font_has_65535_limits(_font);
    var _font_info = font_get_info(_font);
    var _glyphs = _font_info.glyphs;
	
    var byte_len = string_byte_length(_text);
	
    // Reset buffers
    buffer_seek(input_buff, buffer_seek_start, 0);
    buffer_seek(output_buff, buffer_seek_start, 0);
	
    // Write input buffer
    buffer_write(input_buff, buffer_text, _text);
    buffer_seek(input_buff, buffer_seek_start, 0);
	
    while (buffer_tell(input_buff) < byte_len) {
        parse_emoji_chain(input_buff, output_buff, _glyphs, _font_tag, _font_limited, byte_len);
    }
	
    buffer_seek(output_buff, buffer_seek_start, 0);
    var parsed_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";
	
    buffer_resize(input_buff, 0);
    buffer_resize(output_buff, 0);
	
    return parsed_str;
}

function parse_emoji_chain(_input_buff, _output_buff, _glyphs, _font_tag, _font_limited, _byte_len) {
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
			parse_font_glyph(emoji_buffer, _output_buff, _glyphs, _font_tag, _font_limited);
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

function parse_font_glyph(_emoji_buffer, _output_buff, _glyphs, _font_tag, _font_limited) {
    // Convert buffer to lookup key
	buffer_seek(_emoji_buffer, buffer_seek_start, 0);
    var sequence_key = buffer_read(_emoji_buffer, buffer_text);
	
	// Lookup by full sequence first
    var _sprite_index = _glyphs[$ sequence_key];
    if (_sprite_index != undefined) {
        buffer_write(_output_buff, buffer_text, $"[{_font_tag},{_sprite_index},0]");
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
        var _sprite_index = _glyphs[$ stripped_key];

        if (_sprite_index != undefined) {
            buffer_write(_output_buff, buffer_text, $"[{_font_tag},{_sprite_index},0]");
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
		
		var _sprite_index = _glyphs[$ codepoint];
		
        if (_sprite_index != undefined) {
            buffer_write(_output_buff, buffer_text, $"[{_font_tag},{_sprite_index},0]");
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
function font_has_65535_limits(_font) {
    var _info = font_get_info(_font);
    var _glyphs = _info.glyphs;
    var _glyph_names = struct_get_names(_glyphs);
	
    for (var i = 0; i < array_length(_glyph_names); i++) {
        var _char = _glyph_names[i];
        var _ord = ord(_char);

        // If character is above 65535, GameMaker does not support it properly
        if (_ord > 0xFFFF) {
            return false;
        }
    }

    return true;
}

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



function split_by_unicode_formatting(_text) {
    var result = [];
    var current_format = "ltr";  // Default direction
    var active_stack = [];
    var buffer = "";
    var is_anchored_right = false;
    var first_strong_char = false; // Used to track the first strong directional character per line

    for (var i = 1; i <= string_length(_text); i++) {
        var _char = string_char_at(_text, i);
        var _ord = ord(_char);

        // Handle strong directional overrides
        if (_ord == 0x202D) { // LTR Override
            if (buffer != "") {
                array_push(result, {format: current_format, str: buffer, anchor_right: is_anchored_right});
                buffer = "";
            }
            array_push(active_stack, current_format);
            current_format = "ltr";
            continue;
        }
        if (_ord == 0x202E) { // RTL Override
            if (buffer != "") {
                array_push(result, {format: current_format, str: buffer, anchor_right: is_anchored_right});
                buffer = "";
            }
            array_push(active_stack, current_format);
            current_format = "rtl";
            if (!first_strong_char) {
                is_anchored_right = true; // Ensure full line anchoring
                first_strong_char = true;
            }
            continue;
        }

        // Handle embeddings
        //if (_ord == 0x202A) { // LTR Embedding
        //    array_push(active_stack, current_format);
        //    current_format = "ltr";
        //    continue;
        //}
        //if (_ord == 0x202B) { // RTL Embedding
        //    array_push(active_stack, current_format);
        //    current_format = "rtl";
        //    if (!first_strong_char) {
        //        is_anchored_right = true; // Ensure full line anchoring
        //        first_strong_char = true;
        //    }
        //    continue;
        //}

        // Handle pop formatting
        if (_ord == 0x202C) {
            if (buffer != "") {
                array_push(result, {format: current_format, str: buffer, anchor_right: is_anchored_right});
                buffer = "";
            }
            current_format = array_length(active_stack) ? array_pop(active_stack) : "ltr";
            continue;
        }

        // Handle weak marks
        if (_ord == 0x200E) { // LTR Mark
            if (buffer != "") {
                array_push(result, {format: current_format, str: buffer, anchor_right: is_anchored_right});
                buffer = "";
            }
            continue;
        }
        if (_ord == 0x200F) { // RTL Mark
            if (buffer != "") {
                array_push(result, {format: current_format, str: buffer, anchor_right: is_anchored_right});
                buffer = "";
            }
            continue;
        }

        // Determine anchoring when encountering the first strong directional character
        if (!first_strong_char && is_rtl_character(_char)) {
            is_anchored_right = true;
            first_strong_char = true; // Lock in the anchor decision for this line
        } else if (!first_strong_char && !is_rtl_character(_char) && _char != " ") {
            is_anchored_right = false; // First strong LTR means no right anchor
            first_strong_char = true;
        }

        // Append character to buffer
        buffer += _char;

        // Handle line breaks
        if (_char == "\n") {
            array_push(result, {format: current_format, str: buffer, anchor_right: is_anchored_right});
            buffer = "";
			current_format = "ltr";
            first_strong_char = false; // Reset for the new line
            is_anchored_right = false; // Reset for the next line
        }
    }

    // Push final buffer to result
    if (buffer != "") {
        array_push(result, {format: current_format, str: buffer, anchor_right: is_anchored_right});
    }

    return result;
}

function is_rtl_character(_char) {
    var _ord = ord(_char);

    // Arabic (U+0600 – U+06FF)
    if (_ord >= 0x0600 && _ord <= 0x06FF) return true;
    
    // Arabic Supplement (U+0750 – U+077F)
    if (_ord >= 0x0750 && _ord <= 0x077F) return true;
    
    // Arabic Extended-A (U+08A0 – U+08FF)
    if (_ord >= 0x08A0 && _ord <= 0x08FF) return true;
    
    // Hebrew (U+0590 – U+05FF)
    if (_ord >= 0x0590 && _ord <= 0x05FF) return true;
    
    // Syriac (U+0700 – U+074F)
    if (_ord >= 0x0700 && _ord <= 0x074F) return true;
    
    // Thaana (U+0780 – U+07BF)
    if (_ord >= 0x0780 && _ord <= 0x07BF) return true;
    
    // N'Ko (U+07C0 – U+07FF)
    if (_ord >= 0x07C0 && _ord <= 0x07FF) return true;
    
    // Adlam (U+1E900 – U+1E95F)
    if (_ord >= 0x1E900 && _ord <= 0x1E95F) return true;
    
    return false;
}



//var str = "Hello World!";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "ltr", str: "Hello World!", anchor_right: false}
////]
//var str = "\u202E<Hello World!>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "rtl", str: "Hello World!", anchor_right: true}
////]
//var str = "\u202D<Hello> \u202E<World!>\u202C<Back to normal.>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "ltr", str: "Hello ", anchor_right: false},
////    {format: "rtl", str: "World!", anchor_right: false},
////    {format: "ltr", str: " Back to normal.", anchor_right: false}
////]
//var str = "<Start >\u202B<[R-T-L]>\u202C< Middle >\u202A<[L-T-R]>\u202C< End>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "ltr", str: "Start ‫[R-T-L]‬ Middle ‪[L-T-R]‬ End", anchor_right: false},
////]
//var str = "<First Line>\n\u202E<[Right to Left]>\n<Back to [LTR]>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "ltr", str: "First Line", anchor_right: false},
////    {format: "rtl", str: "Right to Left", anchor_right: true},
////    {format: "ltr", str: "Back to LTR", anchor_right: false}
////]
//var str = "<Start >\u200F<Marked Section End>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "ltr", str: "Start ", anchor_right: false},
////    {format: "rtl", str: "Marked Section", anchor_right: true},
////    {format: "ltr", str: " End", anchor_right: false}
////]
//var str = "\u202E<RTL Override >\u200E<but this part is LTR!>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "rtl", str: "RTL Override ", anchor_right: true},
////    {format: "ltr", str: "but this part is LTR!", anchor_right: false}
////]
//var str = "\u202E<1234 is a number but still LTR in RTL context.>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "rtl", str: " 1234 is a number but still LTR in RTL context.", anchor_right: true}
////]
//var str = "<LTR 😊 >\u202E<This is RTL! 😎>\u202C< Back to normal.>";
//show_debug_message(str);
//show_debug_message(split_by_unicode_formatting(str));
//show_debug_message("");
////[
////    {format: "ltr", str: "LTR 😊 ", anchor_right: false},
////    {format: "rtl", str: "This is RTL! 😎", anchor_right: true},
////    {format: "ltr", str: " Back to normal.", anchor_right: false}
////]


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

