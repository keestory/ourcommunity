-- Read-only AFTER 001, BEFORE LOGIN/secret activation. No SET ROLE is necessary.
-- A result other than the single role_configuration row requires review.
WITH runtime AS (SELECT * FROM pg_roles WHERE rolname='ourcommunity_preview_runtime'), results AS (
 SELECT 'missing_runtime_role'::text category,'ourcommunity_preview_runtime'::text object,'{}'::jsonb detail
 WHERE NOT EXISTS (SELECT 1 FROM runtime)
 UNION ALL
 SELECT 'missing_schema','ourcommunity_preview','{}'::jsonb WHERE to_regnamespace('ourcommunity_preview') IS NULL
 UNION ALL
 SELECT 'role_configuration'::text category,r.rolname::text object,
        jsonb_build_object('login',r.rolcanlogin,'superuser',r.rolsuper,'createdb',r.rolcreatedb,
          'createrole',r.rolcreaterole,'replication',r.rolreplication,'bypassrls',r.rolbypassrls,
          'connection_limit',r.rolconnlimit) detail FROM runtime r
 UNION ALL
 SELECT 'membership',parent.rolname,'{}'::jsonb FROM pg_auth_members m JOIN runtime r ON r.oid=m.member
 JOIN pg_roles parent ON parent.oid=m.roleid
 UNION ALL
 SELECT 'database_create',current_database(),'{}'::jsonb FROM runtime r
 WHERE has_database_privilege(r.oid,current_database(),'CREATE')
 UNION ALL
 SELECT 'schema_create',n.nspname,'{}'::jsonb FROM pg_namespace n CROSS JOIN runtime r
 WHERE n.nspname !~ '^pg_' AND has_schema_privilege(r.oid,n.oid,'CREATE')
 UNION ALL
 SELECT 'external_relation',n.nspname||'.'||c.relname,'{}'::jsonb FROM pg_class c
 JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN runtime r
 WHERE n.nspname NOT IN ('pg_catalog','information_schema','ourcommunity_preview') AND n.nspname !~ '^pg_'
 AND c.relkind IN ('r','p','v','m','f') AND has_schema_privilege(r.oid,n.oid,'USAGE')
 AND (has_table_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
      OR has_any_column_privilege(r.oid,c.oid,'SELECT,INSERT,UPDATE,REFERENCES'))
 UNION ALL
 SELECT 'external_sequence',n.nspname||'.'||c.relname,'{}'::jsonb FROM pg_class c
 JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN runtime r
 WHERE n.nspname NOT IN ('pg_catalog','information_schema','ourcommunity_preview') AND n.nspname !~ '^pg_'
 AND c.relkind='S' AND has_schema_privilege(r.oid,n.oid,'USAGE') AND has_sequence_privilege(r.oid,c.oid,'SELECT,USAGE,UPDATE')
 UNION ALL
 SELECT 'external_function',n.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')','{}'::jsonb
 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace CROSS JOIN runtime r
 WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
 AND has_schema_privilege(r.oid,n.oid,'USAGE') AND has_function_privilege(r.oid,p.oid,'EXECUTE')
 UNION ALL
 SELECT 'runtime_object_owner',n.nspname||'.'||c.relname,'{}'::jsonb FROM pg_class c
 JOIN pg_namespace n ON n.oid=c.relnamespace CROSS JOIN runtime r
 WHERE n.nspname='ourcommunity_preview' AND c.relowner=r.oid
 UNION ALL
 SELECT 'missing_rls',n.nspname||'.'||c.relname,'{}'::jsonb FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='ourcommunity_preview' AND c.relkind='r' AND c.relname NOT IN ('guests','guest_gate','leases')
 AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity)
)
SELECT category,object,detail FROM results ORDER BY category,object;
