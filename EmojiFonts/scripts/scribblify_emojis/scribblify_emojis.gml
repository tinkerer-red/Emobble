var t1 = scribble_fallback_font;

function is_emoji_codepoint(_codepoint) {
    return (
		(_codepoint >= 0x0600) || //honestly anything past hebrew is probably fine
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

function scribblify_emojis(input_string, _sprite, _lookup_table, _font=undefined) {
	#region Set up Optimizers
	static read_buff = buffer_create(0, buffer_grow, 1);
	static emoji_buff = buffer_create(0, buffer_grow, 1);
	static input_buff = buffer_create(0, buffer_grow, 1);
	static output_buff = buffer_create(0, buffer_grow, 1);
	
	//micro optimization
	var _read_buff = read_buff;
	var _emoji_buff = emoji_buff;
	var _input_buff = input_buff;
	var _output_buff = output_buff;
	
	// Pre-allocate sizes
	var _byte_len = string_byte_length(input_string);
	buffer_resize(_input_buff, _byte_len)
	buffer_resize(_output_buff, _byte_len)
	
	// Write input buffer
	buffer_write(_input_buff, buffer_text, input_string);
	buffer_seek(_input_buff, buffer_seek_start, 0)
	
	#endregion
	
	// Constants
	var __ZeroWidthJoiner = 0x200D; // used to combine two emojis together
	var __VariationSelector = 0xFE0F; //usually used for alternate emoji drawing, or drawing a regular char as an emoji
	var __SkinTonesMin = 0x1F3FB; // The lower end of the skin tones
	var __SkinTonesMax = 0x1F400; // The upper end of the skin tones
	
	// Variables
	var _sprite_name = sprite_get_name(_sprite);
	
	//used for keeping track of the last found replacement
	var _previous_codepoint = undefined;
	var _codepoint = undefined;
	
	while (buffer_tell(_input_buff) < _byte_len) {
		_codepoint = buffer_read_codepoint(_input_buff);

		if (is_emoji_codepoint(_codepoint)) {
			//not needed as resizing it at the end will handle this for us
			///buffer_seek(_emoji_buff, buffer_seek_start, 0);

			// Include previous codepoint if it's a variation
			if (_previous_codepoint != undefined) {
				if (_codepoint == __VariationSelector) {
					buffer_write_codepoint(_emoji_buff, _previous_codepoint);
				}
				else {
					buffer_write_codepoint(_output_buff, _previous_codepoint);
					_previous_codepoint = undefined;
				}
			}

			// Collect full emoji sequence
			var _reach_eob = false; //reached end of buffer
			while (is_emoji_codepoint(_codepoint)) {
				//show_debug_message($"Added codepoint :: {_codepoint} :: '{chr(_codepoint)}'")
				buffer_write_codepoint(_emoji_buff, _codepoint);
				if (buffer_tell(_input_buff) >= _byte_len) {
					_reach_eob = true;
					break;
				}
				_codepoint = buffer_read_codepoint(_input_buff);
			}

			var emoji_len = buffer_tell(_emoji_buff);
			var read_pos = 0;
			//show_debug_message($"searching for emojis :: emoji_len = {emoji_len}, read_pos = {read_pos}")
			// Match longest substrings first
			while (read_pos < emoji_len) {
				var matched = false;

				for (var length = emoji_len - read_pos; length > 0; length--) {
					//read the text of the emoji
					buffer_copy(_emoji_buff, read_pos, length, _read_buff, 0);
					var _candidate = buffer_read(_read_buff, buffer_text);
					buffer_resize(_read_buff, 0);
					
					//show_debug_message($"Attempting to find _candidate :: '{_candidate}'")
					
					if (_lookup_table[$ _candidate] != undefined) {
						//show_debug_message($"Found _candidate :: '{_candidate}'")
						var _frame_index = _lookup_table[$ _candidate];
						var _replacement = $"[{_sprite_name},{_frame_index},0]";
						buffer_write(_output_buff, buffer_text, _replacement);

						read_pos += length;
						matched = true;
						break;
					}
				}

				if (!matched) {
					//show_debug_message($"matched no emojis")
					var cp = buffer_peek(_emoji_buff, read_pos, buffer_u8);
					buffer_write(_output_buff, buffer_u8, cp);
					read_pos += 1;
				}
			}
			
			buffer_resize(_emoji_buff, 0)
			
			//if end of buffer, break.
			if (_reach_eob) {
				break;
			}
			
			_previous_codepoint = _codepoint;
			_codepoint = undefined;
		}
		else {
			if (_previous_codepoint != undefined) {
				buffer_write_codepoint(_output_buff, _previous_codepoint);
			}
			_previous_codepoint = _codepoint;
			_codepoint = undefined;
		}
	}

	// Final replacement in case we end on a valid match
	if (_previous_codepoint != undefined) {
		buffer_write_codepoint(_output_buff, _previous_codepoint);
	}
	
	// Convert buffer back to string
	buffer_seek(_output_buff, buffer_seek_start, 0);
	var result = buffer_read(_output_buff, buffer_text);
	
	#region Clean up Optimizers
	buffer_resize(_input_buff, 0);
	buffer_resize(_output_buff, 0);
	#endregion
	
	return result;
}


//show_debug_message(scribblify_emojis("Hello 😊 World", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Good job 👍🏽 Buddy", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Family 👨‍👩‍👧‍👦 Day", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Heart ❤️ Check", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Star ★ vs ✩", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Fire 🔥 Emoji", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Wave 👋🏾 Test", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Person 🚶‍♀️ Walking", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("⚠️ Warning Label", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Moon 🌕 vs 🌑", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Snowman ☃️ Test", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Email ✉️ Check", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Check ✔️ or ❌", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Numbers ➀ ➁ ➂", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Scissors ✂️ Cut", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Invisible 🤺 Man", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Kiss 💋 Mark", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Arrow ⬆️⬇️⬅️➡️", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Dagger 🗡️ Test", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Superhero 🦸‍♂️ Power", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// 🛠 Edge Cases & Stress Testing

//// ✅ Incorrectly formatted start (special characters)
//show_debug_message("")
//show_debug_message(scribblify_emojis("@#$% 😊 Test", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("!123 ❤️ Numbers", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Incorrectly formatted end (junk characters)
//show_debug_message("")
//show_debug_message(scribblify_emojis("End of Test 😎 %^&*", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Final ✅ 123!!!", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Unicode + Emoji Mix
//show_debug_message("")
//show_debug_message(scribblify_emojis("漢字 ❤️ Test", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("¡Hola! 👋🏽 ¿Cómo estás?", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Special ASCII Sequences
//show_debug_message("")
//show_debug_message(scribblify_emojis("ASCII Test *^_^* ☺️", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("Emoticon :) converted? 😃", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Emoji Sequences with Extra Spaces
//show_debug_message("")
//show_debug_message(scribblify_emojis("    Extra Space 😊 Test    ", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("👨‍👩‍👦‍👦     Family with space", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Unicode Control Characters
//show_debug_message("")
//show_debug_message(scribblify_emojis("Test\u200BHidden Zero Width Space", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("🚀 Rocket\u202ETest Right-To-Left", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Overloaded Emojis & Symbols
//show_debug_message("")
//show_debug_message(scribblify_emojis("🔴🔵⚫⚪🔺🔻🔸🔹🔶🔷 Stars & Shapes", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("♠️♥️♣️♦️ Cards", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Broken / Partial Emoji Data
//show_debug_message("")
//show_debug_message(scribblify_emojis("🚀 Rocket \u1F680 Broken", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("\u200D\u200D Zero Width Joiners", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Double Emojis Stacked
//show_debug_message("")
//show_debug_message(scribblify_emojis("🎵🎶 Music Notes Together", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("💡💬 Ideas & Chat", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));

//// ✅ Extreme Edge Case: Long Mixed Emoji String
//show_debug_message("")
//show_debug_message(scribblify_emojis("🤔🤷‍♂️💭 Thinking... 🤔🤷‍♂️💭", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
//show_debug_message(scribblify_emojis("👩‍🚀👨‍🚀🧑‍🚀 Astronaut Crew 👩‍🚀👨‍🚀🧑‍🚀", __emj_noto_deluxe_32, __emoji_lookup_noto_deluxe()));
