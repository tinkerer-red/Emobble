// This is a generated file from `build_gml.py` — do not modify.
function emobble_get_ord(_name) {
	if (is_undefined(_name)) return -1;
	static __map = json_parse("{escaped}");
	var key = string_lower(string(_name));
	key = string_replace_all(key, " ", "_");
	key = string_replace_all(key, "-", "_");
	if (variable_struct_exists(__map, key)) return __map[$ key];
	return -1;
}
