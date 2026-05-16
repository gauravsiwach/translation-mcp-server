-- Schema extracted from CNC_DB1 binary dump
-- Schema: customer_uat_ind

CREATE TABLE customer_uat_ind.pepsi_content (
id bigint NOT NULL,
language character varying(10) NOT NULL,
version numeric(10,2) NOT NULL,
url text,
applicable_from timestamp with time zone,
title character varying(255),
status character varying(20) DEFAULT 'PUBLISHED'::character varying NOT NULL,
type character varying(50) DEFAULT 'TERMS_AND_CONDITIONS'::character varying NOT NULL,
published_at timestamp with time zone,
content text,
content_with_html text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
is_public boolean,
customer_type character varying(50),
content_key character varying(100),
data jsonb,
CONSTRAINT chk_pepsi_legal_terms_status_1 CHECK (((status)::text = ANY (ARRAY['ACTIVE'::text, 'DEPRECATED'::text, 'DRAFT'::text, 'ARCHIVED'::text, 'PUBLISHED'::text]))),
CONSTRAINT chk_pepsi_legal_terms_type_1 CHECK (((type)::text = ANY (ARRAY['TERMS_AND_CONDITIONS'::text, 'TERMS_AND_CONDITIONS_CHECKOUT'::text, 'PRIVACY_POLICY'::text, 'GDPR_POLICY'::text, 'GDPR_ADDITIONAL_POLICY'::text, 'LEGAL_POLICY'::text, 'OTHERS'::text])));

CREATE TABLE customer_uat_ind.pepsi_customer_config (
customer_id character varying(100) NOT NULL,
preferences jsonb NOT NULL,
consent jsonb NOT NULL,
metadata jsonb,
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
created_by character varying(100),
updated_by character varying(100);

CREATE TABLE customer_uat_ind.pepsi_customers (
customer_id character varying(100) NOT NULL,
distributor_id character varying(100) NOT NULL,
user_id character varying(100),
site_id integer,
idp_id character varying(255),
okta_status character varying(50),
first_name character varying(100),
last_name character varying(100),
second_last_name character varying(100),
user_type character varying(50),
email character varying(190),
phone character varying(50),
account_status character varying(50) DEFAULT 'ACTIVE'::character varying NOT NULL,
is_active boolean DEFAULT true,
email_verified boolean DEFAULT false,
phone_verified boolean DEFAULT false,
is_profile_complete boolean DEFAULT false,
is_test_user boolean DEFAULT false NOT NULL,
data jsonb,
address jsonb,
created_by character varying(100),
updated_by character varying(100),
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
CONSTRAINT chk_pepsi_customers_account_status CHECK (((account_status)::text = ANY (ARRAY[('ACTIVE'::character varying)::text, ('INACTIVE'::character varying)::text, ('PENDING'::character varying)::text, ('SUSPENDED'::character varying)::text, ('DELETED'::character varying)::text]))),
CONSTRAINT chk_pepsi_customers_user_type CHECK (((user_type)::text = ANY (ARRAY[('STORE_OWNER'::character varying)::text, ('STORE_MANAGER'::character varying)::text, ('BUYER'::character varying)::text, ('ADMIN'::character varying)::text, ('SALES_REP'::character varying)::text, ('OTHER'::character varying)::text])));

CREATE TABLE customer_uat_ind.pepsi_distributors (
distributor_id character varying(100) NOT NULL,
name character varying(255),
category character varying(50),
state_code character varying(10),
contact_person character varying(100),
contact_number character varying(50),
address jsonb,
is_active boolean DEFAULT true,
created_by character varying(100),
updated_by character varying(100),
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
sales_hierarchy jsonb DEFAULT '{}'::jsonb NOT NULL
);


CREATE TABLE customer_uat_ind.pepsi_filemetadata (
id bigint NOT NULL,
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
updated_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
data jsonb NOT NULL
);


CREATE TABLE customer_uat_ind.pepsi_folder (
folder_id character varying(100) NOT NULL,
name character varying(255) NOT NULL,
created_datetime timestamp with time zone NOT NULL,
updated_datetime timestamp with time zone NOT NULL
);


CREATE TABLE customer_uat_ind.pepsi_languages (
language_code character varying(10) NOT NULL,
language character varying(100) NOT NULL,
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
updated_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE customer_uat_ind.pepsi_legal_terms (
id bigint NOT NULL,
language character varying(10) NOT NULL,
version numeric(10,2) NOT NULL,
url text,
applicable_from timestamp with time zone,
title character varying(255),
status character varying(20) DEFAULT 'PUBLISHED'::character varying NOT NULL,
type character varying(50) DEFAULT 'TERMS_AND_CONDITIONS'::character varying NOT NULL,
published_at timestamp with time zone,
content text,
content_with_html text,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
is_public boolean,
customer_type character varying(50),
content_key character varying(100),
CONSTRAINT chk_pepsi_legal_terms_status CHECK (((status)::text = ANY (ARRAY['ACTIVE'::text, 'DEPRECATED'::text, 'DRAFT'::text, 'ARCHIVED'::text, 'PUBLISHED'::text]))),
CONSTRAINT chk_pepsi_legal_terms_type CHECK (((type)::text = ANY (ARRAY['TERMS_AND_CONDITIONS'::text, 'TERMS_AND_CONDITIONS_CHECKOUT'::text, 'PRIVACY_POLICY'::text, 'GDPR_POLICY'::text, 'GDPR_ADDITIONAL_POLICY'::text, 'LEGAL_POLICY'::text, 'OTHERS'::text])));

CREATE TABLE customer_uat_ind.pepsi_pace_sync (
id bigint NOT NULL,
entity_type character varying(50) NOT NULL,
entity_id character varying(100) NOT NULL,
batch_id character varying(100),
operation character varying(20) NOT NULL,
sync_source character varying(20) DEFAULT 'PACE'::character varying,
process_status character varying(20) NOT NULL,
error_message text,
payload_snapshot jsonb,
event_timestamp timestamp with time zone,
created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
CONSTRAINT chk_pepsi_pace_sync_entity_type CHECK (((entity_type)::text = ANY (ARRAY[('CUSTOMER'::character varying)::text, ('DISTRIBUTOR'::character varying)::text]))),
CONSTRAINT chk_pepsi_pace_sync_operation CHECK (((operation)::text = ANY (ARRAY[('UPSERT'::character varying)::text, ('DELETE'::character varying)::text]))),
CONSTRAINT chk_pepsi_pace_sync_process_status CHECK (((process_status)::text = ANY (ARRAY[('PENDING'::character varying)::text, ('PROCESSING'::character varying)::text])));

CREATE TABLE customer_uat_ind.pepsi_segment (
segment_id character varying(100) NOT NULL,
name character varying(255) NOT NULL,
description character varying(255),
folder_id character varying(100) NOT NULL,
source character varying(50) NOT NULL,
updated_by character varying(100) NOT NULL,
status character varying(30) NOT NULL,
data jsonb NOT NULL,
created_datetime timestamp with time zone NOT NULL,
updated_datetime timestamp with time zone NOT NULL,
last_edited_page character varying(50) DEFAULT 'SETUP'::character varying NOT NULL,
CONSTRAINT pepsi_segment_last_edited_page_check CHECK (((last_edited_page)::text = ANY (ARRAY[('SETUP'::character varying)::text, ('REVIEW'::character varying)::text]))),
CONSTRAINT pepsi_segment_source_check CHECK (((source)::text = ANY (ARRAY[('PACE'::character varying)::text]))),
CONSTRAINT pepsi_segment_status_check CHECK (((status)::text = ANY (ARRAY[('DRAFT'::character varying)::text, ('PUBLISHED'::character varying)::text])));

CREATE TABLE customer_uat_ind.pepsi_segment_category (
category_id character varying(100) NOT NULL,
category_name character varying(255) NOT NULL,
data jsonb NOT NULL,
created_datetime timestamp with time zone NOT NULL,
updated_datetime timestamp with time zone NOT NULL
);


CREATE TABLE customer_uat_ind.pepsi_store_segments (
id bigint NOT NULL,
store_id character varying(100) NOT NULL,
segment_id character varying(100) NOT NULL,
data jsonb,
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
updated_datetime timestamp with time zone NOT NULL
);


CREATE TABLE customer_uat_ind.pepsi_stores (
store_id character varying(100) NOT NULL,
store_name character varying(190),
customer_id character varying(100),
location_id character varying(100),
location_type character varying(255),
site_id integer,
store_type character varying(255),
gtmu_id character varying(10),
relationship_type_code character varying(10),
group_code character varying(10),
active_status boolean DEFAULT true,
is_registered boolean DEFAULT false,
is_default boolean DEFAULT false,
registration_date timestamp with time zone,
last_active_date timestamp with time zone,
data jsonb,
address jsonb,
contacts jsonb,
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
updated_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
created_by character varying(20),
updated_by character varying(20),
enhancements jsonb,
registration_status character varying(20);

CREATE TABLE customer_uat_ind.pepsi_translations (
id bigint NOT NULL,
label text NOT NULL,
language_code character varying(10) NOT NULL,
translation text NOT NULL,
type character varying(255),
created_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
updated_datetime timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE customer_uat_ind.pepsi_web_metadata (
id bigint NOT NULL,
customer_id character varying(100) NOT NULL,
wa_id character varying(100) NOT NULL,
metadata jsonb
);


CREATE TABLE customer_uat_ind.pepsi_web_tokens (
temp_token character varying(100) NOT NULL,
metadata jsonb,
customer_id character varying(100) NOT NULL
);


ALTER TABLE customer_uat_ind.pepsi_content ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
SEQUENCE NAME customer_uat_ind.pepsi_content_id_seq
START WITH 1
INCREMENT BY 1
NO MINVALUE
NO MAXVALUE
CACHE 1;

ALTER TABLE customer_uat_ind.pepsi_filemetadata ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
SEQUENCE NAME customer_uat_ind.pepsi_filemetadata_id_seq
START WITH 0
INCREMENT BY 1
MINVALUE 0
NO MAXVALUE
CACHE 1;

ALTER TABLE customer_uat_ind.pepsi_legal_terms ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
SEQUENCE NAME customer_uat_ind.pepsi_legal_terms_id_seq
START WITH 1
INCREMENT BY 1
NO MINVALUE
NO MAXVALUE
CACHE 1;

ALTER TABLE customer_uat_ind.pepsi_pace_sync ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
SEQUENCE NAME customer_uat_ind.pepsi_pace_sync_id_seq
START WITH 1
INCREMENT BY 1
NO MINVALUE
NO MAXVALUE
CACHE 1;

ALTER TABLE customer_uat_ind.pepsi_store_segments ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
SEQUENCE NAME customer_uat_ind.pepsi_store_segments_id_seq2
START WITH 1
INCREMENT BY 1
NO MINVALUE
NO MAXVALUE
CACHE 1;

ALTER TABLE customer_uat_ind.pepsi_translations ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY (
SEQUENCE NAME customer_uat_ind.pepsi_translations_id_seq
START WITH 1
INCREMENT BY 1
NO MINVALUE
NO MAXVALUE
CACHE 1;

ALTER TABLE ONLY customer_uat_ind.pepsi_folder
ADD CONSTRAINT pepsi_folder_pkey PRIMARY KEY (folder_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_languages
ADD CONSTRAINT pepsi_languages_pkey PRIMARY KEY (language_code);

ALTER TABLE ONLY customer_uat_ind.pepsi_legal_terms
ADD CONSTRAINT pepsi_legal_terms_pkey PRIMARY KEY (id);

ALTER TABLE ONLY customer_uat_ind.pepsi_content
ADD CONSTRAINT pepsi_legal_terms_pkey_1 PRIMARY KEY (id);

ALTER TABLE ONLY customer_uat_ind.pepsi_segment_category
ADD CONSTRAINT pepsi_segment_category_pkey PRIMARY KEY (category_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_segment
ADD CONSTRAINT pepsi_segment_pkey PRIMARY KEY (segment_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_customer_config
ADD CONSTRAINT pk_pepsi_customer_config PRIMARY KEY (customer_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_customers
ADD CONSTRAINT pk_pepsi_customers_customer_id PRIMARY KEY (customer_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_distributors
ADD CONSTRAINT pk_pepsi_distributors_code PRIMARY KEY (distributor_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_filemetadata
ADD CONSTRAINT pk_pepsi_filemetadata PRIMARY KEY (id);

ALTER TABLE ONLY customer_uat_ind.pepsi_pace_sync
ADD CONSTRAINT pk_pepsi_pace_sync_id PRIMARY KEY (id);

ALTER TABLE ONLY customer_uat_ind.pepsi_stores
ADD CONSTRAINT pk_pepsi_stores PRIMARY KEY (store_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_web_tokens
ADD CONSTRAINT pk_pepsi_web_tokens PRIMARY KEY (temp_token);

ALTER TABLE ONLY customer_uat_ind.pepsi_web_metadata
ADD CONSTRAINT pkey_pepsi_web_metadata PRIMARY KEY (id);

ALTER TABLE ONLY customer_uat_ind.pepsi_customer_config
ADD CONSTRAINT fk_pepsi_customer_config_customer_id FOREIGN KEY (customer_id) REFERENCES customer_uat_ind.pepsi_customers(customer_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_customers
ADD CONSTRAINT fk_pepsi_customers_distributor_id FOREIGN KEY (distributor_id) REFERENCES customer_uat_ind.pepsi_distributors(distributor_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_store_segments
ADD CONSTRAINT fk_pepsi_store_segments_segment FOREIGN KEY (segment_id) REFERENCES customer_uat_ind.pepsi_segment(segment_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_store_segments
ADD CONSTRAINT fk_pepsi_store_segments_store FOREIGN KEY (store_id) REFERENCES customer_uat_ind.pepsi_stores(store_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_stores
ADD CONSTRAINT fk_pepsi_stores_customer_id FOREIGN KEY (customer_id) REFERENCES customer_uat_ind.pepsi_customers(customer_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_translations
ADD CONSTRAINT fk_pepsi_translations_language_code FOREIGN KEY (language_code) REFERENCES customer_uat_ind.pepsi_languages(language_code);

ALTER TABLE ONLY customer_uat_ind.pepsi_web_tokens
ADD CONSTRAINT fk_pepsi_web_tokens_customer_id FOREIGN KEY (customer_id) REFERENCES customer_uat_ind.pepsi_customers(customer_id);

ALTER TABLE ONLY customer_uat_ind.pepsi_segment
ADD CONSTRAINT fk_segment_folder FOREIGN KEY (folder_id) REFERENCES customer_uat_ind.pepsi_folder(folder_id);

