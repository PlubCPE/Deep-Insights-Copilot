-- templates/logins_by_app_version.sql
SELECT app_version, count(*) as attempts,
       sum(case when success_flag then 1 else 0 end) as success
FROM analytics.fact_logins
WHERE app_channel = :app_channel::text
  AND login_ts between :start_date::timestamp and :end_date::timestamp
GROUP BY app_version
ORDER BY attempts desc
LIMIT :top_n::int;
