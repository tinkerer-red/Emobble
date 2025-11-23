/// @func draw_texture_part(_tex_index, _tex_x, _tex_y, _tex_w, _tex_h, _x, _y)
/// @desc Draw part of a texture at a position using a vertex buffer.
function draw_texture_part(_tex_index, _tex_x, _tex_y, _tex_w, _tex_h, _x, _y)
{
    // Reusable format and buffer
    static _vertex_buffer = vertex_create_buffer();
    static _vertex_format = undefined;
	
    if (_vertex_format == undefined)
    {
        vertex_format_begin();
        vertex_format_add_position();
        vertex_format_add_colour();
        vertex_format_add_texcoord();
        _vertex_format = vertex_format_end();
    }
	
    var _texture_tw = texture_get_texel_width(_tex_index);
    var _texture_th = texture_get_texel_height(_tex_index);
	
    var _u0 = _tex_x * _texture_tw;
    var _v0 = _tex_y * _texture_th;
    var _u1 = (_tex_x + _tex_w) * _texture_tw;
    var _v1 = (_tex_y + _tex_h) * _texture_th;
	
    var _x0 = _x;
    var _y0 = _y;
    var _x1 = _x + _tex_w;
    var _y1 = _y + _tex_h;
	
    vertex_begin(_vertex_buffer, _vertex_format);
	
    // Triangle strip: TL, TR, BL, BR
    vertex_position(_vertex_buffer, _x0, _y0);
    vertex_colour(_vertex_buffer, c_white, 1);
    vertex_texcoord(_vertex_buffer, _u0, _v0);

    vertex_position(_vertex_buffer, _x1, _y0);
    vertex_colour(_vertex_buffer, c_white, 1);
    vertex_texcoord(_vertex_buffer, _u1, _v0);

    vertex_position(_vertex_buffer, _x0, _y1);
    vertex_colour(_vertex_buffer, c_white, 1);
    vertex_texcoord(_vertex_buffer, _u0, _v1);

    vertex_position(_vertex_buffer, _x1, _y1);
    vertex_colour(_vertex_buffer, c_white, 1);
    vertex_texcoord(_vertex_buffer, _u1, _v1);

    vertex_end(_vertex_buffer);
    vertex_submit(_vertex_buffer, pr_trianglestrip, _tex_index);
}
