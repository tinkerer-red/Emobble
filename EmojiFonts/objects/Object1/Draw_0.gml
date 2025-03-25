/// @description Insert description here
// You can write your code in this editor

var _sep = 3

// Scrolling
if (mouse_wheel_down()) {
	yy -= 30
}
if (mouse_wheel_up()) {
	yy += 30
}

// Dragging
if (mouse_check_button_pressed(mb_left)) {
	mouse_y_start = mouse_y;
    drag_y_start = yy; // Store initial position
}
if (mouse_check_button(mb_left)) {
	var drag_offset = mouse_y - mouse_y_start;
    yy = drag_y_start + drag_offset; // Adjust position based on drag offset
}

// Dragging
if (mouse_check_button_pressed(mb_middle)) {
	mouse_middle_y_start = mouse_y;
}
if (mouse_check_button(mb_middle)) {
	yy -= (mouse_y - mouse_middle_y_start) / 10;
}

/// Line drawing
var _lines = string_count("\n", get_emojis());
var _height = 16 + _sep;
draw_set_alpha(0.1)
for(var _i=0; _i<_lines; _i+=2){
	draw_rectangle(
		0,
		yy+(_i*_height),
		1280,
		yy+((_i+1)*_height),
		false
	)
}
draw_set_alpha(1)

//// Render all
var _off = 16, xx = 16;
//for (var i=0; i<array_length(emoji_strings); i++){
//	scribble(emoji_strings[i]).draw(xx,yy)
//	xx+=_off;
//}
//
//scribble(unicode_string).draw(xx,yy)


scribble(final_string).draw(xx,yy)