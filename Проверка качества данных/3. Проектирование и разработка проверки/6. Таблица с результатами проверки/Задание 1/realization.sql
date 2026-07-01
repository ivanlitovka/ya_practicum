CREATE TABLE Stage.dq_checks_results (
    Table_name varchar(255),
    DQ_check_name varchar(255),
    Datetime timestamp,
    DQ_check_result numeric(8,2)
);
COMMENT ON COLUMN Stage.dq_checks_results.DQ_check_result IS 'Результат выполнения проверки качества данных: 0 — данные прошли проверку, 1 — данные не прошли проверку';