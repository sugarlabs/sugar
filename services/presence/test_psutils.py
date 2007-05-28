from psutils import escape_identifier

assert escape_identifier('') == '_'
assert escape_identifier('_') == '_5f'
assert escape_identifier('1') == '_31'
assert escape_identifier('a1') == 'a1'
assert escape_identifier('1a') == '_31a'
assert escape_identifier("0123abc_xyz\x01\xff") == '_30123abc_5fxyz_01_ff'
