# -*- coding: utf-8 -*-

import pyparsing

class Parser(object): # pragma: nocover

	def parse(self, s):
		field = pyparsing.Word(pyparsing.alphanums)
		operator = pyparsing.oneOf(('==', '!=', '>', '<', '>=', '<='))
		value = pyparsing.quotedString | pyparsing.Word(pyparsing.alphanums)

		and_or = pyparsing.oneOf(['and', 'or'], caseless=True)

		field_op_value = field + operator + value

		andor_field_op_value = and_or + field_op_value

		pattern = field_op_value + pyparsing.Optional(pyparsing.OneOrMore(andor_field_op_value))

		print(pattern.parseString(s))


if __name__ == '__main__': # pragma: nocover

	p = Parser()

	for s in [
		'foo=="bar"',
		'foo == "bar"',
		'a > b',
		'a < 2',
		'foo=="bar" and 1 > 2',
		'foo=="bar" and 1 > 2 or foo > bar',
	]:
		print(s)
		p.parse(s)
		print("----")
