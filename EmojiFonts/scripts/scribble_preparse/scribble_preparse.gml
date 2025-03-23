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
	static emoji_buff = buffer_create(0, buffer_grow, 1); // Static buffer for emoji sequences
    
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

