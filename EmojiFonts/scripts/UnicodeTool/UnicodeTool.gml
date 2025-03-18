function UnicodeTool(_str) {
    // Convert input string to a standard Unicode format if necessary
    var _unicode_str = detect_encoding_and_convert(_str);
    return new __UnicodeToolClass(_unicode_str);
}

function __UnicodeToolClass(_unicode_str) constructor {
    my_unicode = _unicode_str;
    
    static utf8 = function() {
        return unicode_to_utf8(my_unicode);
    };
    
    static utf8hex = function() {
        return unicode_to_utf8hex(my_unicode);
    };
    
    static utf16 = function() {
        return unicode_to_utf16(my_unicode);
    };
    
    static utf32 = function() {
        return unicode_to_utf32(my_unicode);
    };
    
    static base64 = function() {
        return unicode_to_base64(my_unicode);
    };
    
    static url = function() {
        return unicode_to_url(my_unicode);
    };
    
    static decimal = function() {
        return unicode_to_decimal(my_unicode);
    };
    
    static toString = function() {
        return my_unicode;
    };
}

function detect_encoding_and_convert(_str) {
    // You could detect patterns like:
    // - UTF-8 hex: \xF0\x9F\x80\x84
    // - UTF-16: \uD83C\uDC04
    // - UTF-32: u+0001F004
    // - Decimal: 55356 56324
    // - URL encoding: %F0%9F%80%84
    // - Base64: (Detect valid base64 pattern)

    // Placeholder: Assume input is already Unicode for now
    return _str;
}

function decimal_to_hex(_decimal, _padding) {
    var hex = "";
    
    while (_decimal > 0) {
        var remainder = _decimal mod 16;
        _decimal = _decimal div 16;
        
        if (remainder < 10) {
            hex = chr(48 + remainder) + hex;  // Convert 0-9
        } else {
            hex = chr(87 + remainder) + hex;  // Convert a-f
        }
    }
    
    while (string_length(hex) < _padding) {
        hex = "0" + hex;  // Ensure proper padding (e.g., 6 digits for UTF-32)
    }
    
    return hex;
}

/// Checks if a code unit is a high surrogate (first part of a surrogate pair)
function is_high_surrogate(_code_unit) {
    return (_code_unit >= 0xD800) && (_code_unit <= 0xDBFF);
}

/// Converts a high and low surrogate into a proper Unicode codepoint
function to_codepoint(_high_surrogate, _low_surrogate) {
    return ((_high_surrogate - 0xD800) << 10) + (_low_surrogate - 0xDC00) + 0x10000;
}

/// Converts a single hex character ('0'-'9', 'a'-'f', 'A'-'F') to its integer value.
/// This function only takes in integers values and not strings
/// Returns -1 if the character is invalid.
///@ignore
function __hex_to_int(_hex) {
	//hex bit 2
	if (_hex >= ord("0") && _hex <= ord("9")) { // '0'-'9'
		return _hex - ord("0");
	}
	else if (_hex >= ord("A") && _hex <= ord("F")) { // 'A'-'F'
		return _hex - ord("A") + 10;
	}
	else if (_hex >= ord("a") && _hex <= ord("f")) { // 'a'-'f'
		return _hex - ord("a") + 10;
	}
	
	return -1;
}

function unicode_to_utf8(_unicode) {
    var utf8_str = "";

    for (var i = 1; i <= string_length(_unicode); i++) {
        var codepoint = string_ord_at(_unicode, i);

        if (codepoint <= 0x7F) {
            // ASCII (1 byte)
            utf8_str += chr(codepoint);
        } else if (codepoint <= 0x7FF) {
            // 2-byte sequence
            utf8_str += chr(0xC0 | (codepoint >> 6));
            utf8_str += chr(0x80 | (codepoint & 0x3F));
        } else if (codepoint <= 0xFFFF) {
            // 3-byte sequence
            utf8_str += chr(0xE0 | (codepoint >> 12));
            utf8_str += chr(0x80 | ((codepoint >> 6) & 0x3F));
            utf8_str += chr(0x80 | (codepoint & 0x3F));
        } else {
            // 4-byte sequence (for characters outside BMP)
            utf8_str += chr(0xF0 | (codepoint >> 18));
            utf8_str += chr(0x80 | ((codepoint >> 12) & 0x3F));
            utf8_str += chr(0x80 | ((codepoint >> 6) & 0x3F));
            utf8_str += chr(0x80 | (codepoint & 0x3F));
        }
    }

    return utf8_str;
}
function unicode_to_utf8hex(_unicode) {
    var hex_str = "";
    
    for (var i = 1; i <= string_length(_unicode); i++) {
        var codepoint = string_ord_at(_unicode, i);
        
        if (codepoint <= 0x7F) { 
            // 1-byte UTF-8 (ASCII)
            hex_str += "\\x" + decimal_to_hex(codepoint, 2);
        } else if (codepoint <= 0x7FF) {  
            // 2-byte UTF-8
            hex_str += "\\x" + decimal_to_hex(0xC0 | (codepoint >> 6), 2);
            hex_str += "\\x" + decimal_to_hex(0x80 | (codepoint & 0x3F), 2);
        } else if (codepoint <= 0xFFFF) {  
            // 3-byte UTF-8
            hex_str += "\\x" + decimal_to_hex(0xE0 | (codepoint >> 12), 2);
            hex_str += "\\x" + decimal_to_hex(0x80 | ((codepoint >> 6) & 0x3F), 2);
            hex_str += "\\x" + decimal_to_hex(0x80 | (codepoint & 0x3F), 2);
        } else {  
            // 4-byte UTF-8 (for emojis and extended characters)
            hex_str += "\\x" + decimal_to_hex(0xF0 | (codepoint >> 18), 2);
            hex_str += "\\x" + decimal_to_hex(0x80 | ((codepoint >> 12) & 0x3F), 2);
            hex_str += "\\x" + decimal_to_hex(0x80 | ((codepoint >> 6) & 0x3F), 2);
            hex_str += "\\x" + decimal_to_hex(0x80 | (codepoint & 0x3F), 2);
        }
    }
    
    return hex_str;
}
function unicode_to_utf16(_unicode) {
    var utf16 = "";
    
    for (var i = 1; i <= string_length(_unicode); i++) {
        var codepoint = string_ord_at(_unicode, i);

        if (codepoint <= 0xFFFF) {  
            // Normal UTF-16
            utf16 += "\\u" + decimal_to_hex(codepoint, 4);
        } else {  
            // UTF-16 Surrogate Pair (High + Low)
            var high = 0xD800 | ((codepoint - 0x10000) >> 10);
            var low = 0xDC00 | ((codepoint - 0x10000) & 0x3FF);
            utf16 += "\\u" + decimal_to_hex(high, 4) + "\\u" + decimal_to_hex(low, 4);
        }
    }
    
    return utf16;
}
function unicode_to_utf32(_unicode) {
    var utf32 = "";
    
    for (var i = 1; i <= string_length(_unicode); i++) {
        var codepoint = string_ord_at(_unicode, i);
        utf32 += "u+" + decimal_to_hex(codepoint, 8);  
    }
    
    return utf32;
}
function unicode_to_base64(_unicode) {
    return base64_encode(_unicode);
}
function unicode_to_url(_unicode) {
    var url_encoded = "";
    
    for (var i = 1; i <= string_length(_unicode); i++) {
        var codepoint = string_ord_at(_unicode, i);
        
        if (codepoint <= 0x7F) {  
            // ASCII (direct)
            url_encoded += chr(codepoint);
        } else {  
            // Convert to UTF-8 bytes
            var utf8 = unicode_to_utf8hex(chr(codepoint));
            url_encoded += string_replace_all(utf8, "\\x", "%");
        }
    }
    
    return url_encoded;
}
function unicode_to_decimal(_unicode) {
    var decimal_str = "";
    
    for (var i = 1; i <= string_length(_unicode); i++) {
        var codepoint = string_ord_at(_unicode, i);
        
        if (codepoint >= 0x10000) {
            // Split into surrogate pair
            var high = 0xD800 | ((codepoint - 0x10000) >> 10);
            var low = 0xDC00 | ((codepoint - 0x10000) & 0x3FF);
            decimal_str += string(high) + " " + string(low) + " ";
        } else {
            decimal_str += string(codepoint) + " ";
        }
    }
    
    return string_trim(decimal_str);
}

function utf8_to_unicode(_utf8) {
    static input_buff = buffer_create(0, buffer_grow, 1);
	static output_buff = buffer_create(0, buffer_grow, 1);
    
	if (string_length(_utf8) == 0) return "";
	
    var byte_len = string_byte_length(_utf8);
    
	//reset buffers
	buffer_seek(input_buff, buffer_seek_start, 0);
	buffer_seek(output_buff, buffer_seek_start, 0);
	
	//write input buffer
	buffer_write(input_buff, buffer_text, _utf8)
	buffer_seek(input_buff, buffer_seek_start, 0);
	
    var i = 0;
	while (i < byte_len) {
        var byte1 = buffer_read(input_buff, buffer_u8); i++;
        var codepoint = 0;

        if (byte1 < 0x80) {
            // Single-byte ASCII (0xxxxxxx)
            codepoint = byte1;
        }
        else if ((byte1 & 0xE0) == 0xC0) {
            // Two-byte sequence (110xxxxx 10xxxxxx)
            var byte2 = buffer_read(input_buff, buffer_u8); i++;
            codepoint = ((byte1 & 0x1F) << 6) | (byte2 & 0x3F);
        }
        else if ((byte1 & 0xF0) == 0xE0) {
            // Three-byte sequence (1110xxxx 10xxxxxx 10xxxxxx)
            var byte2 = buffer_read(input_buff, buffer_u8); i++;
            var byte3 = buffer_read(input_buff, buffer_u8); i++;
            codepoint = ((byte1 & 0x0F) << 12) | ((byte2 & 0x3F) << 6) | (byte3 & 0x3F);
        }
        else if ((byte1 & 0xF8) == 0xF0) {
            // Four-byte sequence (11110xxx 10xxxxxx 10xxxxxx 10xxxxxx)
            var byte2 = buffer_read(input_buff, buffer_u8); i++;
            var byte3 = buffer_read(input_buff, buffer_u8); i++;
            var byte4 = buffer_read(input_buff, buffer_u8); i++;
            codepoint = ((byte1 & 0x07) << 18) | ((byte2 & 0x3F) << 12) | ((byte3 & 0x3F) << 6) | (byte4 & 0x3F);
        }
        else {
            // Invalid UTF-8 sequence, replace with ▯ (9647)
            codepoint = 9647;
        }

        // Write the Unicode codepoint into the buffer
        buffer_write(output_buff, buffer_u8, codepoint);
    }

    // Convert the buffer into a proper Unicode string
    buffer_seek(output_buff, buffer_seek_start, 0);
    var unicode_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";
    
	buffer_resize(input_buff, 0);
	buffer_resize(output_buff, 0);
	
    return unicode_str;
}
function utf8hex_to_unicode(_utf8hex) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);

    if (string_length(_utf8hex) == 0) return "";
	
    var byte_len = string_byte_length(_utf8hex);

    // Reset buffers
    buffer_seek(input_buff, buffer_seek_start, 0);
    buffer_seek(output_buff, buffer_seek_start, 0);

    // Write input buffer
    buffer_write(input_buff, buffer_text, _utf8hex);
    buffer_seek(input_buff, buffer_seek_start, 0);

    var i = 0;
	while (i < byte_len) {
        var byte1 = buffer_read(input_buff, buffer_u8); i++;

		// Detect `\x` sequence
		if (byte1 == ord("\\")) // First byte is "\"
		&& (i < byte_len) {
			var byte2 = buffer_read(input_buff, buffer_u8); i++;
				
			if ((byte2 == ord("x"))
			&& (i < byte_len)) {
				// Read next two bytes as hex digits
				var hex1 = buffer_read(input_buff, buffer_u8);
				var hex2 = buffer_read(input_buff, buffer_u8);
				i += 2;
				
				// Convert hex1 and hex2 from ASCII to actual byte values
				hex1 = __hex_to_int(hex1);
				hex2 = __hex_to_int(hex2);
					
				if (hex1 >= 0 && hex2 >= 0) {
					// Combine hex values into a single byte
					var byte_value = (hex1 << 4) | hex2;
					// Write the decoded byte into the output buffer
					buffer_write(output_buff, buffer_u8, byte_value);
					continue;
				}
			}
			//else {
			//	// If "\x" isn't followed by two hex digits, write it as is
			//	buffer_write(output_buff, buffer_u8, byte1);
			//	buffer_write(output_buff, buffer_u8, byte2);
			//	continue;
			//}
		}

		// If it's not part of `\x`, just write it directly
		buffer_write(output_buff, buffer_u8, byte1);
    }
	
	
    // Convert the buffer into a proper Unicode string
    buffer_seek(output_buff, buffer_seek_start, 0);
    var unicode_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";

    buffer_resize(input_buff, 0);
    buffer_resize(output_buff, 0);

    return unicode_str;
}
function utf16_to_unicode(_utf16) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);
    
	if (string_length(_utf16) == 0) return "";
	
    var byte_len = string_byte_length(_utf16);

    // Reset buffers
    buffer_seek(input_buff, buffer_seek_start, 0);
    buffer_seek(output_buff, buffer_seek_start, 0);

    // Write input buffer
    buffer_write(input_buff, buffer_text, _utf16);
    buffer_seek(input_buff, buffer_seek_start, 0);

    var i = 0;
    var high_surrogate = 0;  // Store high surrogate if found

    while (i < byte_len) {
        var byte1 = buffer_read(input_buff, buffer_u8); i++;

        // Detect `\u` sequence
        if (byte1 == ord("\\")) { // First byte is "\"
            if (i < byte_len) {
                var byte2 = buffer_read(input_buff, buffer_u8); i++;

                if (byte2 == ord("u")) {
                    var hex_count = 0;
					var code_unit = 0;
					var _post_add = false;
                    // Read up to 4 hex digits
                    while (hex_count < 4 && i < byte_len) {
                        var next_byte = buffer_read(input_buff, buffer_u8); i++;
                        var hex_val = __hex_to_int(next_byte);
                        
						if (hex_val < 0) {
							_post_add = true;
							break;  // Stop if not a valid hex digit
						}
                        
						code_unit = (code_unit << 4) | hex_val;
                        hex_count++;
                    }

                    // **Handle Surrogate Pairs (4-byte UTF-16)**
                    if (is_high_surrogate(high_surrogate)) {
                        var codepoint = to_codepoint(high_surrogate, code_unit);

                        // Write UTF-8 encoded character
                        buffer_write_codepoint(output_buff, codepoint);
                        high_surrogate = 0; // Reset after use
                        continue;
                    }

                    // If it's a high surrogate, store it for the next iteration
                    if (is_high_surrogate(code_unit)) {
                        high_surrogate = code_unit;
                        continue;
                    }
					
					if (code_unit) {
		                // Otherwise, write as a normal Unicode character
		                buffer_write_codepoint(output_buff, code_unit);
					}
					
					// If we stopped on an early exit unicode add that next byte after
					if (_post_add) {
						buffer_write_codepoint(output_buff, next_byte);
					}
                    continue;
                }
            }
        }

        // If it's not part of `\uXXXX`, just write it directly
        buffer_write(output_buff, buffer_u8, byte1);
    }

    // Convert the buffer into a proper Unicode string
    buffer_seek(output_buff, buffer_seek_start, 0);
	
    var unicode_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";
	
    buffer_resize(input_buff, 0);
    buffer_resize(output_buff, 0);

    return unicode_str;
}


function utf32_to_unicode(_utf32) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);
	
    if (string_length(_utf32) == 0) return "";
	
    var byte_len = string_byte_length(_utf32);
	
    // Reset buffers
    buffer_seek(input_buff, buffer_seek_start, 0);
    buffer_seek(output_buff, buffer_seek_start, 0);
	
    // Write input buffer
    buffer_write(input_buff, buffer_text, _utf32);
    buffer_seek(input_buff, buffer_seek_start, 0);
	
    var i = 0;
	
    while (i < byte_len) {
        var byte1 = buffer_read(input_buff, buffer_u8); i++;
		
        // Detect `\U` sequence (UTF-32)
         if (byte1 == ord("u") || byte1 == ord("U")) { // First byte is "\"
            if (i < byte_len) {
                var byte2 = buffer_read(input_buff, buffer_u8); i++;
				
                if (byte2 == ord("+") && (i + 4) <= byte_len) {
                    // Read next eight bytes as hex digits
                    var hex1 = buffer_read(input_buff, buffer_u8);
                    var hex2 = buffer_read(input_buff, buffer_u8);
                    var hex3 = buffer_read(input_buff, buffer_u8);
                    var hex4 = buffer_read(input_buff, buffer_u8);
                    var hex5 = buffer_read(input_buff, buffer_u8);
                    var hex6 = buffer_read(input_buff, buffer_u8);
                    var hex7 = buffer_read(input_buff, buffer_u8);
                    var hex8 = buffer_read(input_buff, buffer_u8);
                    i += 8;

                    // Convert hex digits into their integer values
                    hex1 = __hex_to_int(hex1);
                    hex2 = __hex_to_int(hex2);
                    hex3 = __hex_to_int(hex3);
                    hex4 = __hex_to_int(hex4);
                    hex5 = __hex_to_int(hex5);
                    hex6 = __hex_to_int(hex6);
                    hex7 = __hex_to_int(hex7);
                    hex8 = __hex_to_int(hex8);

                    if (hex1 >= 0 && hex2 >= 0 && hex3 >= 0 && hex4 >= 0 && 
                        hex5 >= 0 && hex6 >= 0 && hex7 >= 0 && hex8 >= 0) {
                        
                        // Combine hex values into a single 32-bit codepoint
                        var codepoint = (hex1 << 28) | (hex2 << 24) | (hex3 << 20) | (hex4 << 16) |
                                        (hex5 << 12) | (hex6 << 8) | (hex7 << 4) | hex8;

                        // **Encode as UTF-8 before writing**
                        buffer_write_codepoint(output_buff, codepoint);
                        continue;
                    }
                }
            }
        }
		
        // If it's not part of `\UXXXXXXXX`, just write it directly
        buffer_write(output_buff, buffer_u8, byte1);
    }
	
    // Convert the buffer into a proper Unicode string
    buffer_seek(output_buff, buffer_seek_start, 0);
    var unicode_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";
	
	buffer_resize(input_buff, 0);
	buffer_resize(output_buff, 0);
	
    return unicode_str;
}
function base64_to_unicode(_base64) {
    return base64_decode(_base64);
}
function url_to_unicode(_url) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);

    if (string_length(_url) == 0) return "";
	
    var byte_len = string_byte_length(_url);

    // Reset buffers
    buffer_seek(input_buff, buffer_seek_start, 0);
    buffer_seek(output_buff, buffer_seek_start, 0);

    // Write input buffer
    buffer_write(input_buff, buffer_text, _url);
    buffer_seek(input_buff, buffer_seek_start, 0);

    var i = 0;

    while (i < byte_len) {
        var byte1 = buffer_read(input_buff, buffer_u8); i++;

        // Detect `%XX` sequence
        if (byte1 == ord("%")) {
            if (i + 2 <= byte_len) { // Ensure at least two more bytes exist
                var hex1 = buffer_read(input_buff, buffer_u8);
                var hex2 = buffer_read(input_buff, buffer_u8);
                i += 2;

                // Convert hex digits
                var int_hex1 = __hex_to_int(hex1);
                var int_hex2 = __hex_to_int(hex2);

                if (int_hex1 >= 0 && int_hex2 >= 0) {
                    // Combine hex values into a single byte
                    var decoded_byte = (int_hex1 << 4) | int_hex2;
                    buffer_write(output_buff, buffer_u8, decoded_byte);
                    continue;
                }
				
				// If invalid, write `%ZZ` where Z is the original characters
                buffer_write(output_buff, buffer_u8, ord("%"));
                buffer_write(output_buff, buffer_u8, hex1);
                buffer_write(output_buff, buffer_u8, hex2);
                continue;
            }
        }

        // If it's not part of `%XX`, just write it directly
        buffer_write(output_buff, buffer_u8, byte1);
    }

    // Convert the buffer into a proper Unicode string
    buffer_seek(output_buff, buffer_seek_start, 0);
    var unicode_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";

    buffer_resize(input_buff, 0);
    buffer_resize(output_buff, 0);

    return unicode_str;
}
function int_to_unicode(_int_str) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);

    if (string_length(_int_str) == 0) return "";
	
    var byte_len = string_byte_length(_int_str);

    // Reset buffers
    buffer_seek(input_buff, buffer_seek_start, 0);
    buffer_seek(output_buff, buffer_seek_start, 0);

    // Write input buffer
    buffer_write(input_buff, buffer_text, _int_str);
    buffer_seek(input_buff, buffer_seek_start, 0);

    var i = 0;
    var codepoint = 0;

    while (i < byte_len) {
        var byte1 = buffer_read(input_buff, buffer_u8); i++;
        byte1 = (byte1 >= ord("0") && byte1 <= ord("9")) ? byte1 - ord("0") : -1;

        // If we are at the last character AND it's a valid number, store it before processing
        if (i >= byte_len && byte1 != -1) {
            codepoint = (codepoint * 10) + byte1;
        }

        if (byte1 == -1 || i >= byte_len) {
            // Convert collected number to Unicode
            if (codepoint > 0) {
                buffer_write_codepoint(output_buff, codepoint);
                codepoint = 0; // Reset for next number
            }
        }
		else {
            codepoint = (codepoint * 10) + byte1;
        }
    }

    // Convert the buffer into a proper Unicode string
    buffer_seek(output_buff, buffer_seek_start, 0);
    var unicode_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";

    buffer_resize(input_buff, 0);
    buffer_resize(output_buff, 0);

    return unicode_str;
}
function decimal_to_unicode(_decimal) {
    static input_buff = buffer_create(0, buffer_grow, 1);
    static output_buff = buffer_create(0, buffer_grow, 1);
	
	if (string_length(_decimal) == 0) return "";
	
    var byte_len = string_byte_length(_decimal);

    // Reset buffers
    buffer_seek(input_buff, buffer_seek_start, 0);
    buffer_seek(output_buff, buffer_seek_start, 0);

    // Write input buffer
    buffer_write(input_buff, buffer_text, _decimal);
    buffer_seek(input_buff, buffer_seek_start, 0);

    var i = 0;
    var low_surrogate = 0;
	var high_surrogate = 0;
    while (i < byte_len) {
        var byte1 = buffer_read(input_buff, buffer_u8); i++;
        byte1 = (byte1 >= ord("0") && byte1 <= ord("9")) ? byte1 - ord("0") : -1;

        if (i >= byte_len && byte1 != -1) {
            low_surrogate = (low_surrogate * 10) + byte1;
        }

        if (byte1 == -1 || i >= byte_len) {
            // Convert collected number to Unicode
            if (low_surrogate > 0) {
				// **Handle Surrogate Pairs (4-byte UTF-16)**
                if (is_high_surrogate(high_surrogate)) {
                    var codepoint = to_codepoint(high_surrogate, low_surrogate);
                              
                    // Write the proper UTF-8 encoded character into buffer
                    buffer_write_codepoint(output_buff, codepoint);
                    continue;
                }
				
				if (is_high_surrogate(low_surrogate)) {
					// Combine hex values into a single 16-bit value
					high_surrogate = low_surrogate;
					low_surrogate = 0;
					continue;
				}
				
				// Normal Unicode character (BMP)
	            buffer_write_codepoint(output_buff, low_surrogate);
	            // Reset for next number
                low_surrogate = 0;
				continue;
            }
        }
		else {
            low_surrogate = (low_surrogate * 10) + byte1;
        }
    }

    // Convert the buffer into a proper Unicode string
    buffer_seek(output_buff, buffer_seek_start, 0);
    var unicode_str = buffer_get_size(output_buff) ? buffer_read(output_buff, buffer_text) : "";

    buffer_resize(input_buff, 0);
    buffer_resize(output_buff, 0);

    return unicode_str;
}

#region Tests 1
/*
repeat(5)show_debug_message("===")
show_debug_message("\u") // ""
show_debug_message("\uf") // ""
show_debug_message("\uff") // "ÿ"
show_debug_message("\ufff") // "࿿"
show_debug_message("\u1") // ""
show_debug_message("\u11") // ""
show_debug_message("\u111") // "đ"
show_debug_message("\u1111") // "ᄑ"
show_debug_message("\u0001") // ""
show_debug_message("\u0011") // ""
show_debug_message("\u0111") // "đ"
show_debug_message("\u1111") // "ᄑ"

var converter = UnicodeTool("🀄");
show_debug_message(converter); // 🀄
show_debug_message(converter.utf8()); // ð
show_debug_message(converter.utf8hex()); // \xF0\x9F\x80\x84
show_debug_message(converter.utf16());  // \uD83C\uDC04
show_debug_message(converter.utf32());  // u+0001F004
show_debug_message(converter.url());  // %F0%9F%80%84
show_debug_message(converter.decimal()); // 55356 56324
repeat(2)show_debug_message("")

// UTF-8 to Unicode Tests
show_debug_message(utf8_to_unicode("ð")); // 🀄 (U+1F004)
show_debug_message(utf8_to_unicode("\xF0\x9F\x92\xA9")); // 💩 (U+1F4A9)
show_debug_message(utf8_to_unicode("\xE2\x9C\x85")); // ✅ (U+2705)
show_debug_message(utf8_to_unicode("hello")); // "hello"
repeat(2)show_debug_message("")

// UTF-8 Hex to Unicode Tests
show_debug_message(utf8hex_to_unicode(@'\xF0\x9F\x80\x84')); // 🀄 (U+1F004)
show_debug_message(utf8hex_to_unicode(@'\xF0\x9F\x92\xA9')); // 💩 (U+1F4A9)
show_debug_message(utf8hex_to_unicode(@'\xE2\x9C\x85')); // ✅ (U+2705)
show_debug_message(utf8hex_to_unicode(@'\x68\x65\x6C\x6C\x6F')); // "hello"
repeat(2)show_debug_message("")

// UTF-16 to Unicode Tests
show_debug_message(utf16_to_unicode("\\uD83D\\uDE00")); // 😀 (U+1F600)
show_debug_message(utf16_to_unicode("\\uD83D\\uDC36")); // 🐶 (U+1F436)
show_debug_message(utf16_to_unicode("\\uD83D\\uDC69\\u200D\\uD83D\\uDCBB")); // 👩‍💻 (Woman Technologist)
show_debug_message(utf16_to_unicode("\\u2603")); // ☃ (U+2603)
show_debug_message(utf16_to_unicode("Hello \\u0021")); // Hello !
repeat(2)show_debug_message("")

// UTF-32 to Unicode Tests
show_debug_message(utf32_to_unicode("u+0001F004")); // 🀄 (U+1F004)
show_debug_message(utf32_to_unicode("U+0001F4A9")); // 💩 (U+1F4A9)
show_debug_message(utf32_to_unicode("U+00002705")); // ✅ (U+2705)
show_debug_message(utf32_to_unicode("hello")); // "hello"
repeat(2)show_debug_message("")

// URL to Unicode Tests
show_debug_message(url_to_unicode("%F0%9F%80%84")); // 🀄 (U+1F004)
show_debug_message(url_to_unicode("%F0%9F%92%A9")); // 💩 (U+1F4A9)
show_debug_message(url_to_unicode("%E2%9C%85")); // ✅ (U+2705)
show_debug_message(url_to_unicode("%68%65%6C%6C%6F")); // "hello"
repeat(2)show_debug_message("")

// Decimal to Unicode Tests
show_debug_message(decimal_to_unicode("55356 56324")); // 🀄 (U+1F004)
show_debug_message(decimal_to_unicode("55357 56489")); // 💩 (U+1F4A9)
show_debug_message(decimal_to_unicode("55356 57225")); // 🎉 (U+1F389)
show_debug_message(decimal_to_unicode("55357 56832")); // 😀 (U+1F600)
show_debug_message(decimal_to_unicode("72 101 108 108 111")); // "Hello"
show_debug_message(decimal_to_unicode("49 48 48 37")); // "100%"
repeat(2)show_debug_message("")

// Integer to Unicode Tests
show_debug_message(int_to_unicode(string(0x1F600))); // 😀 (U+1F600)
show_debug_message(int_to_unicode(string(0x1F4A9))); // 💩 (U+1F4A9)
show_debug_message(int_to_unicode(string(0x2705))); // ✅ (U+2705)
show_debug_message(int_to_unicode(string(0x0048))); // "H"
show_debug_message(int_to_unicode(string(128169))); // 💩 (U+1F4A9)
repeat(2)show_debug_message("")

// Edge Cases & Invalid Inputs
show_debug_message(utf8_to_unicode("")); // Should return ""
show_debug_message(utf8hex_to_unicode(@'')); // Should return ""
show_debug_message(utf16_to_unicode("\\uZZZZ")); // Should return placeholder ▯
show_debug_message(utf32_to_unicode("U+ZZZZZZZZ")); // Should return placeholder ▯
show_debug_message(url_to_unicode("%ZZ%ZZ%ZZ")); // Should return placeholder ▯
show_debug_message(decimal_to_unicode("9999999999")); // Should return placeholder ▯
show_debug_message(int_to_unicode(-1)); // Should return ""

/// ✅ Basic BMP Characters
var _char = "\u2603";
var _return = utf16_to_unicode("\\u2603");
show_debug_message($"{_return} == \u2603 :: {_return == _char ? "True" : "False"}"); // ☃ (U+2603)

var _char = "\u0041"; // A
var _return = utf16_to_unicode("\\u0041");
show_debug_message($"{_return} == \u0041 :: {_return == _char ? "True" : "False"}"); // A (U+0041)

var _char = "\u00A9"; // ©
var _return = utf16_to_unicode("\\u00A9");
show_debug_message($"{_return} == \u00A9 :: {_return == _char ? "True" : "False"}"); // © (U+00A9)

/// ✅ Surrogate Pair Test (Full UTF-16)
var _char = "😀"; // 😀
var _return = utf16_to_unicode("\\uD83D\\uDE00");
show_debug_message($"{_return} == 😀 :: {_return == _char ? "True" : "False"}"); // 😀 (U+1F600)

var _char = "🐶"; // 🐶
var _return = utf16_to_unicode("\\uD83D\\uDC36");
show_debug_message($"{_return} == 🐶 :: {_return == _char ? "True" : "False"}"); // 🐶 (U+1F436)

/// ✅ Emoji Sequence with Zero Width Joiner (ZWJ)
var _char = "👩‍💻"; // 👩‍💻
var _return = utf16_to_unicode("\\uD83D\\uDC69\\u200D\\uD83D\\uDCBB");
show_debug_message($"{_return} == 👩‍💻 :: {_return == _char ? "True" : "False"}"); // 👩‍💻

/// ✅ Edge Cases - Unexpected Spaces & Characters
var _char = "\u 2603"; 
var _return = utf16_to_unicode("\\u 2603");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u 2603"

var _char = "\u26 03"; 
var _return = utf16_to_unicode("\\u26 03");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u26 03"

var _char = "\u260H"; 
var _return = utf16_to_unicode("\\u260H");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u260H"

/// ✅ Incomplete Unicode Sequence
var _char = "\u"; 
var _return = utf16_to_unicode("\\u");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u"

var _char = "\u2"; 
var _return = utf16_to_unicode("\\u2");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u2"

var _char = "\u26"; 
var _return = utf16_to_unicode("\\u26");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u26"

var _char = "\u260"; 
var _return = utf16_to_unicode("\\u260");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u260"

/// ✅ Handling of Invalid Hexadecimal Digits
var _char = "\uGHIJ"; 
var _return = utf16_to_unicode("\\uGHIJ");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\uGHIJ"

var _char = "\u2X03"; 
var _return = utf16_to_unicode("\\u2X03");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u2X03"

var _char = "\u26YZ"; 
var _return = utf16_to_unicode("\\u26YZ");
show_debug_message($"{_return} == {_char} :: {_return == _char ? "True" : "False"}"); // Expect: "\u26YZ"

/// ✅ Valid 1-4 Character Sequences
var _char = "\uF"; 
var _return = utf16_to_unicode("\\uF");
show_debug_message($"{_return} == \uF :: {_return == _char ? "True" : "False"}"); //  (U+000F)

var _char = "\uFF"; 
var _return = utf16_to_unicode("\\uFF");
show_debug_message($"{_return} == \uFF :: {_return == _char ? "True" : "False"}"); // ÿ (U+00FF)

var _char = "\uFFF"; 
var _return = utf16_to_unicode("\\uFFF");
show_debug_message($"{_return} == \uFFF :: {_return == _char ? "True" : "False"}"); // ࿿ (U+0FFF)

var _char = "\u111"; 
var _return = utf16_to_unicode("\\u111");
show_debug_message($"{_return} == \u111 :: {_return == _char ? "True" : "False"}"); // đ (U+0111)

var _char = "\u1111"; 
var _return = utf16_to_unicode("\\u1111");
show_debug_message($"{_return} == \u1111 :: {_return == _char ? "True" : "False"}"); // ᄑ (U+1111)

var _char = "\u0001"; 
var _return = utf16_to_unicode("\\u0001");
show_debug_message($"{_return} == \u0001 :: {_return == _char ? "True" : "False"}"); //  (U+0001)

var _char = "\u0011"; 
var _return = utf16_to_unicode("\\u0011");
show_debug_message($"{_return} == \u0011 :: {_return == _char ? "True" : "False"}"); //  (U+0011)

var _char = "\u0111"; 
var _return = utf16_to_unicode("\\u0111");
show_debug_message($"{_return} == \u0111 :: {_return == _char ? "True" : "False"}"); // đ (U+0111)

var _char = "\u1111"; 
var _return = utf16_to_unicode("\\u1111");
show_debug_message($"{_return} == \u1111 :: {_return == _char ? "True" : "False"}"); // ᄑ (U+1111)

//*/
#endregion

