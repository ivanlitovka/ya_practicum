SELECT table_name,
	column_name,
	data_type,
	character_maximum_length,
	column_default,
	is_nullable
FROM information_schema.COLUMNS
WHERE table_schema  = 'public'
ORDER BY 
	table_name ASC,
	ordinal_position ASC;