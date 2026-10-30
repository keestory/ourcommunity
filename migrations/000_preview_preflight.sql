-- Read-only BEFORE applying 001. Run only against the approved project.
-- Returns metadata and PUBLIC privileges; never reads application rows or secrets.
WITH namespaces AS (
 SELECT n.oid,n.nspname,n.nspowner,
        coalesce(bool_or(a.privilege_type='USAGE' AND a.grantee=0),false) public_usage,
        coalesce(bool_or(a.privilege_type='CREATE' AND a.grantee=0),false) public_create
 FROM pg_namespace n
 LEFT JOIN LATERAL aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a ON true
 WHERE n.nspname NOT IN ('pg_catalog','information_schema') AND n.nspname !~ '^pg_'
 GROUP BY n.oid,n.nspname,n.nspowner
), results AS (
 SELECT 'executor'::text category,current_user::text object,
        jsonb_build_object('session_user',session_user,'server_version',current_setting('server_version'),
           'superuser',r.rolsuper,'create_role',r.rolcreaterole,
           'create_schema',has_database_privilege(current_user,current_database(),'CREATE')) detail
 FROM pg_roles r WHERE r.rolname=current_user
 UNION ALL
 SELECT 'name_collision',nspname,jsonb_build_object('kind','schema') FROM pg_namespace WHERE nspname='ourcommunity_preview'
 UNION ALL
 SELECT 'name_collision',rolname,jsonb_build_object('kind','role','login',rolcanlogin)
 FROM pg_roles WHERE rolname IN ('ourcommunity_preview_owner','ourcommunity_preview_runtime')
 UNION ALL
 SELECT 'public_database_create',datname,jsonb_build_object('privilege',a.privilege_type)
 FROM pg_database d CROSS JOIN LATERAL aclexplode(coalesce(d.datacl,acldefault('d',d.datdba))) a
 WHERE d.datname=current_database() AND a.grantee=0 AND a.privilege_type='CREATE'
 UNION ALL
 SELECT 'public_schema_create',nspname,'{}'::jsonb FROM namespaces WHERE public_create
 UNION ALL
 SELECT 'public_relation',n.nspname||'.'||c.relname,jsonb_build_object('kind',c.relkind,'privilege',a.privilege_type)
 FROM pg_class c JOIN namespaces n ON n.oid=c.relnamespace
 CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault(CASE WHEN c.relkind='S' THEN 'S'::"char" ELSE 'r'::"char" END,c.relowner))) a
 WHERE n.public_usage AND c.relkind IN ('r','p','v','m','f','S') AND a.grantee=0
 UNION ALL
 SELECT 'public_column',n.nspname||'.'||c.relname||'.'||col.attname,jsonb_build_object('privilege',a.privilege_type)
 FROM pg_attribute col JOIN pg_class c ON c.oid=col.attrelid JOIN namespaces n ON n.oid=c.relnamespace
 CROSS JOIN LATERAL aclexplode(col.attacl) a
 WHERE n.public_usage AND col.attnum>0 AND NOT col.attisdropped AND a.grantee=0
 UNION ALL
 SELECT 'public_function',n.nspname||'.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||')',
        jsonb_build_object('security_definer',p.prosecdef,'kind',p.prokind,'returns',pg_get_function_result(p.oid),
           'extension',(SELECT e.extname FROM pg_depend d JOIN pg_extension e ON e.oid=d.refobjid
                        WHERE d.classid='pg_proc'::regclass AND d.objid=p.oid AND d.deptype='e' LIMIT 1))
 FROM pg_proc p JOIN namespaces n ON n.oid=p.pronamespace
 CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
 WHERE n.public_usage AND a.grantee=0 AND a.privilege_type='EXECUTE'
)
SELECT category,object,detail FROM results ORDER BY category,object;
