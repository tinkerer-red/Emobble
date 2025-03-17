function numberToWords(_num) {
	if (_num == 0) return "zero";
	
	static __ones = [
		"", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
		"ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
		"seventeen", "eighteen", "nineteen"
	];
	
	static __tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"];
	
	//negative
	if (_num < 0) return $"negative {numberToWords(-_num)}";
	
	// just get the best fitting name
	if (_num < 20) {
		return __ones[_num];
	}
	
	// get the best pair of names (exclude 0 and ten as their included in the previous)
	if (_num < 100) {
		var _header = __tens[_num div 10];
		var _body = (_num mod 10 != 0) ? $" {__ones[_num mod 10]}" : "";
		return _header + _body;
	}
	
	// hundred
	if (_num < 1000) {
		var _header = $"{__ones[_num div 100]} hundred";
		var _body = _num mod 100;
		return (_body != 0) ? $"{_header} {numberToWords(_body)}" : _header;
	}
	
	// thousand
	if (_num < 1000000) {
		var _header = $"{numberToWords(_num div 1000)} thousand";
		var _body = _num mod 1000;
		return (_body != 0) ? $"{_header} {numberToWords(_body)}" : _header;
	}
	
	// mill
	if (_num < 1000000000) {
		var _header = numberToWords(_num div 1000000) + " million";
		var _body = _num mod 1000000;
		return (_body != 0) ? _header + " " + numberToWords(_body) : _header;
	}
	
	//bill
	var _header = numberToWords(_num div 1000000000) + " billion";
	var _body = _num mod 1000000000;
	return (_body != 0) ? _header + " " + numberToWords(_body) : _header;
	
	//in not doing anymore
}

for (var i=-100; i<=1000; i++) {
	show_debug_message($"{i} --> {numberToWords(i)}")
}


