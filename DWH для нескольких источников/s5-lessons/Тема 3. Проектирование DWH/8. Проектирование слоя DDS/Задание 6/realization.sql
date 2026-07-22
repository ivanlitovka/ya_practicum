CREATE table dds.dm_timestamps(
	id serial NOT null PRIMARY KEY,
	ts timestamp NOT NULL,
	YEAR SMALLINT NOT NULL check(YEAR >= 2022 AND YEAR < 2500),
	MONTH SMALLINT NOT NULL check(MONTH >= 1 AND MONTH <= 12),
	DAY SMALLINT NOT NULL check(DAY >= 1 AND DAY <= 31),
	time time NOT NULL,
	date date NOT NULL
);