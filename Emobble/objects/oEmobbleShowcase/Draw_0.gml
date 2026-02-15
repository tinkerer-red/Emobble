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

var _lines = array_length(final_lines);
var _height = 16 + _sep;

if (keyboard_check_pressed(vk_home)) {
	yy = 0;
}
if (keyboard_check_pressed(vk_end)) {
	yy = -_lines*_height + window_get_height();
}

/// Line drawing
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


var xx = 16;

gpu_set_tex_filter(true)
//draw_text(xx, yy, final_string)
scribble(final_string).draw(xx,yy)
gpu_set_tex_filter(false)




var _tex_index = real(2);
var _tex_x     = 1602;
var _tex_y     = 304;
var _tex_w     = 13;
var _tex_h     = 16;

//draw_set_color(c_white)
//draw_rectangle(50, 50, 50+_tex_w, 50+_tex_h, false);
//draw_texture_part(_tex_index, _tex_x, _tex_y, _tex_w, _tex_h, 50, 50)

//var _texture_tw = texture_get_texel_width(_tex_index);
//var _texture_th = texture_get_texel_height(_tex_index);

//var _u0 = _tex_x*_texture_tw;
//var _v0 = _tex_y*_texture_th;
//var _u1 = (_tex_x+_tex_w)*_texture_tw;
//var _v1 = (_tex_y+_tex_h)*_texture_th;


