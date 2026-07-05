-- ============================================================================
-- HOTELDATA HUB - Modelo de Datos (Generado desde MongoDB)
-- Base de datos: hoteldata_hub
-- Generado: Julio 2026
-- ============================================================================
-- Este archivo DDL representa la estructura de las colecciones de MongoDB
-- traducidas a SQL relacional para propositos de diagrama/documentacion.
-- ============================================================================

-- ============================================================================
-- 1. DIMENSIONES (Analytics / Modelo Dimensional)
-- ============================================================================

CREATE TABLE dim_hotels (
    prop_id INTEGER PRIMARY KEY,
    prop_country_id INTEGER,
    prop_starrating INTEGER,
    prop_review_score DOUBLE PRECISION,
    prop_brand_bool BOOLEAN,
    prop_location_score1 DOUBLE PRECISION,
    hotel_label VARCHAR(255),
    loaded_at TIMESTAMP,
    manual_override BOOLEAN,
    name_source VARCHAR(50),
    original_generated_name VARCHAR(255),
    description TEXT,
    display_country_label VARCHAR(255),
    display_name VARCHAR(255),
    hotel_name VARCHAR(255),
    updated_at TIMESTAMP,
    updated_by VARCHAR(100),
    verified_at TIMESTAMP
);

CREATE TABLE dim_destinations (
    srch_destination_id INTEGER PRIMARY KEY,
    destination_label VARCHAR(255),
    loaded_at TIMESTAMP,
    destination_display_name VARCHAR(255),
    destination_name VARCHAR(255)
);

CREATE TABLE dim_visitor_countries (
    visitor_location_country_id INTEGER PRIMARY KEY,
    visitor_country_label VARCHAR(255),
    loaded_at TIMESTAMP,
    country_display_name VARCHAR(255),
    country_name VARCHAR(255)
);

CREATE TABLE dim_sites (
    site_id INTEGER PRIMARY KEY,
    site_label VARCHAR(255),
    loaded_at TIMESTAMP
);

CREATE TABLE dim_dates (
    date_key INTEGER PRIMARY KEY,
    date DATE,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    day_of_week INTEGER,
    loaded_at TIMESTAMP
);

CREATE TABLE dim_promotions (
    promotion_flag BOOLEAN PRIMARY KEY,
    promotion_label VARCHAR(50)
);

CREATE TABLE dim_click_status (
    click_bool BOOLEAN PRIMARY KEY,
    click_status VARCHAR(50)
);

CREATE TABLE dim_reservation_status (
    reserva_bool BOOLEAN PRIMARY KEY,
    reservation_status VARCHAR(50)
);

CREATE TABLE dim_occupancy_profile (
    occupancy_profile_id VARCHAR(50) PRIMARY KEY,
    srch_adults_count INTEGER,
    srch_children_count INTEGER,
    srch_room_count INTEGER,
    occupancy_label VARCHAR(255),
    loaded_at TIMESTAMP
);

CREATE TABLE dim_stay_length_category (
    stay_length_category_id VARCHAR(50) PRIMARY KEY,
    stay_length_category VARCHAR(100),
    min_nights INTEGER,
    max_nights INTEGER
);

CREATE TABLE dim_booking_window_category (
    booking_window_category_id VARCHAR(50) PRIMARY KEY,
    booking_window_category VARCHAR(100),
    min_days INTEGER,
    max_days INTEGER
);

CREATE TABLE dim_price_category (
    price_category_id VARCHAR(50) PRIMARY KEY,
    price_category VARCHAR(100),
    min_price_usd DOUBLE PRECISION,
    max_price_usd DOUBLE PRECISION
);

-- ============================================================================
-- 2. TABLA DE HECHOS (Analytics)
-- ============================================================================

CREATE TABLE fact_hotel_reservations (
    id BIGSERIAL PRIMARY KEY,
    source_record_id VARCHAR(100),
    srch_id INTEGER NOT NULL,
    date_time TIMESTAMP,
    date_key INTEGER REFERENCES dim_dates(date_key),
    site_id INTEGER REFERENCES dim_sites(site_id),
    visitor_location_country_id INTEGER REFERENCES dim_visitor_countries(visitor_location_country_id),
    visitor_hist_starrating DOUBLE PRECISION,
    visitor_hist_adr_usd DOUBLE PRECISION,
    prop_country_id INTEGER,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    prop_starrating INTEGER,
    prop_review_score DOUBLE PRECISION,
    prop_brand_bool BOOLEAN,
    prop_location_score1 DOUBLE PRECISION,
    price_usd DOUBLE PRECISION NOT NULL,
    promotion_flag BOOLEAN REFERENCES dim_promotions(promotion_flag),
    srch_destination_id INTEGER REFERENCES dim_destinations(srch_destination_id),
    srch_length_of_stay INTEGER,
    srch_booking_window INTEGER,
    srch_adults_count INTEGER,
    srch_children_count INTEGER,
    srch_room_count INTEGER,
    click_bool BOOLEAN REFERENCES dim_click_status(click_bool),
    reserva_bool BOOLEAN REFERENCES dim_reservation_status(reserva_bool),
    reservas_brutas_usd DOUBLE PRECISION,
    occupancy_profile_id VARCHAR(50) REFERENCES dim_occupancy_profile(occupancy_profile_id),
    stay_length_category_id VARCHAR(50) REFERENCES dim_stay_length_category(stay_length_category_id),
    booking_window_category_id VARCHAR(50) REFERENCES dim_booking_window_category(booking_window_category_id),
    price_category_id VARCHAR(50) REFERENCES dim_price_category(price_category_id),
    loaded_at TIMESTAMP,
    execution_id VARCHAR(100),
    phase VARCHAR(20)
);

-- ============================================================================
-- 3. SEGURIDAD / AUTENTICACION
-- ============================================================================

CREATE TABLE users (
    id VARCHAR(24) PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    primary_role VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    must_change_password BOOLEAN DEFAULT false,
    temporary_password BOOLEAN DEFAULT false,
    role_ids TEXT, -- JSON array de ObjectId
    settings TEXT, -- JSON object
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    updated_by VARCHAR(100),
    created_by VARCHAR(255)
);

CREATE TABLE roles (
    id VARCHAR(24) PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE permissions (
    id VARCHAR(24) PRIMARY KEY,
    permission_code VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE role_permissions (
    role_id VARCHAR(24) NOT NULL REFERENCES roles(id),
    permission_id VARCHAR(24) NOT NULL REFERENCES permissions(id),
    role_name VARCHAR(50),
    permission_code VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE user_sessions (
    id VARCHAR(24) PRIMARY KEY,
    session_token_hash VARCHAR(64) UNIQUE,
    session_token VARCHAR(255) UNIQUE,
    user_id VARCHAR(24) REFERENCES users(id),
    username VARCHAR(100),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    ip_address VARCHAR(45),
    user_agent TEXT,
    remember_me BOOLEAN DEFAULT false,
    end_reason VARCHAR(50),
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    ended_at TIMESTAMP,
    last_activity_at TIMESTAMP
);

CREATE TABLE user_activity_logs (
    id VARCHAR(24) PRIMARY KEY,
    event_key VARCHAR(100) UNIQUE,
    user_id VARCHAR(24),
    username VARCHAR(100),
    email VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    module VARCHAR(50),
    details TEXT, -- JSON object
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP
);

CREATE TABLE refresh_tokens (
    id VARCHAR(24) PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE,
    user_id VARCHAR(24) REFERENCES users(id),
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    used BOOLEAN DEFAULT false
);

CREATE TABLE password_recovery_tokens (
    id VARCHAR(24) PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE,
    user_id VARCHAR(24) REFERENCES users(id),
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE email_verification_tokens (
    id VARCHAR(24) PRIMARY KEY,
    token_hash VARCHAR(64) UNIQUE,
    user_id VARCHAR(24) REFERENCES users(id),
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE two_factor_codes (
    id VARCHAR(24) PRIMARY KEY,
    user_id VARCHAR(24) REFERENCES users(id),
    code VARCHAR(10),
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE user_2fa (
    id VARCHAR(24) PRIMARY KEY,
    user_id VARCHAR(24) UNIQUE REFERENCES users(id),
    secret VARCHAR(255),
    enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- ============================================================================
-- 4. PARTNER / CONTENIDO DE HOTEL
-- ============================================================================

CREATE TABLE hotel_images (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    image_url VARCHAR(500) NOT NULL,
    title VARCHAR(255),
    source VARCHAR(50),
    demo_seed BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (prop_id, image_url)
);

CREATE TABLE hotel_policies (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER UNIQUE NOT NULL REFERENCES dim_hotels(prop_id),
    room_type_id VARCHAR(100) DEFAULT '',
    check_in_time VARCHAR(10),
    check_out_time VARCHAR(10),
    cancellation_policy TEXT,
    pet_policy TEXT,
    children_policy TEXT,
    extra_bed_policy TEXT,
    payment_policy TEXT,
    house_rules TEXT,
    source VARCHAR(50),
    demo_seed BOOLEAN DEFAULT false,
    min_stay INTEGER DEFAULT 1,
    max_stay INTEGER,
    cancellation_hours INTEGER,
    children_allowed BOOLEAN,
    pets_allowed BOOLEAN,
    pet_fee DOUBLE PRECISION,
    extra_bed_fee DOUBLE PRECISION,
    season_id VARCHAR(50) DEFAULT '',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE hotel_content_pages (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER UNIQUE NOT NULL REFERENCES dim_hotels(prop_id),
    description TEXT,
    highlights TEXT,
    amenities_text TEXT,
    active_amenities TEXT, -- JSON array
    amenities_catalog TEXT, -- JSON array
    room_amenities TEXT, -- JSON object
    amenity_prices TEXT, -- JSON object
    source VARCHAR(50),
    demo_seed BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE hotel_content_changes (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    entity_type VARCHAR(50),
    action VARCHAR(50),
    payload TEXT, -- JSON object
    changed_by VARCHAR(100),
    changed_at TIMESTAMP
);

CREATE TABLE hotel_profile (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER UNIQUE NOT NULL REFERENCES dim_hotels(prop_id),
    display_name VARCHAR(255),
    hotel_name VARCHAR(255),
    address TEXT,
    phone VARCHAR(50),
    wifi_ssid VARCHAR(100),
    wifi_password VARCHAR(100),
    check_in_time VARCHAR(10),
    check_out_time VARCHAR(10),
    breakfast_hours VARCHAR(50),
    restaurant_hours VARCHAR(50),
    gym_hours VARCHAR(50),
    pool_hours VARCHAR(50),
    parking_info TEXT,
    emergency_contact VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE hotel_amenities (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    name VARCHAR(255) NOT NULL,
    icon VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE hotel_profile_changes (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    field VARCHAR(100),
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP,
    reason TEXT,
    source VARCHAR(100)
);

CREATE TABLE corporate_contracts (
    id VARCHAR(24) PRIMARY KEY,
    contract_id VARCHAR(100) UNIQUE NOT NULL,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    company_name VARCHAR(255) NOT NULL,
    contract_code VARCHAR(50) NOT NULL,
    description TEXT,
    discount_percent INTEGER DEFAULT 0,
    fixed_rate DOUBLE PRECISION DEFAULT 0,
    applicable_rate_plan_ids TEXT,
    applicable_room_type_ids TEXT,
    start_date VARCHAR(10),
    end_date VARCHAR(10),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (prop_id, contract_code)
);

CREATE TABLE hotels (
    id VARCHAR(24) PRIMARY KEY,
    hotel_code VARCHAR(100) UNIQUE,
    name VARCHAR(255),
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    phone VARCHAR(50),
    email VARCHAR(255),
    website VARCHAR(255),
    stars INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- ============================================================================
-- 5. INVENTARIO / HABITACIONES
-- ============================================================================

CREATE TABLE room_types (
    id VARCHAR(24) PRIMARY KEY,
    room_type_id VARCHAR(100) UNIQUE NOT NULL,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    name VARCHAR(255),
    description TEXT,
    max_adults INTEGER,
    max_children INTEGER,
    base_capacity INTEGER,
    base_rate DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT true,
    room_number VARCHAR(20),
    floor VARCHAR(10),
    view VARCHAR(100),
    smoking BOOLEAN,
    accessible BOOLEAN,
    is_roh BOOLEAN DEFAULT false,
    features TEXT, -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE hotel_rooms (
    id VARCHAR(24) PRIMARY KEY,
    hotel_room_id VARCHAR(100) UNIQUE NOT NULL,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_type_id VARCHAR(100) REFERENCES room_types(room_type_id),
    room_label VARCHAR(100),
    room_number VARCHAR(20),
    floor VARCHAR(10),
    view VARCHAR(100),
    smoking BOOLEAN,
    accessible BOOLEAN,
    is_active BOOLEAN DEFAULT true,
    is_roh BOOLEAN DEFAULT false,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE room_inventory_calendar (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_type_id VARCHAR(100) NOT NULL REFERENCES room_types(room_type_id),
    date DATE NOT NULL,
    total_rooms INTEGER,
    available_rooms INTEGER,
    blocked_rooms INTEGER DEFAULT 0,
    version INTEGER DEFAULT 1,
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (prop_id, room_type_id, date)
);

CREATE TABLE room_availability_blocks (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_type_id VARCHAR(100) REFERENCES room_types(room_type_id),
    start_date DATE NOT NULL,
    end_date DATE,
    reason VARCHAR(255),
    blocked_rooms INTEGER,
    room_numbers TEXT, -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE blackout_dates (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_type_id VARCHAR(100),
    room_label VARCHAR(100),
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    source VARCHAR(50),
    reason TEXT,
    created_at TIMESTAMP
);

CREATE TABLE room_features (
    id VARCHAR(24) PRIMARY KEY,
    label VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50)
);

CREATE TABLE hotel_products (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    product_id VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    UNIQUE (prop_id, product_id)
);

CREATE TABLE platform_earnings (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) UNIQUE NOT NULL,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    commission_pct DOUBLE PRECISION,
    booking_total DOUBLE PRECISION,
    commission_amount DOUBLE PRECISION,
    status VARCHAR(50),
    created_at TIMESTAMP
);

-- ============================================================================
-- 6. RESERVACIONES
-- ============================================================================

CREATE TABLE booking_orders (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) UNIQUE NOT NULL,
    user_id VARCHAR(24) REFERENCES users(id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    status VARCHAR(50) NOT NULL,
    booking_source VARCHAR(50),
    guest_name VARCHAR(255),
    guest_email VARCHAR(255),
    guest_phone VARCHAR(50),
    room_type_id VARCHAR(100),
    check_in_date DATE,
    check_out_date DATE,
    adults INTEGER,
    children INTEGER DEFAULT 0,
    rooms INTEGER DEFAULT 1,
    comment TEXT,
    special_requests TEXT, -- JSON array
    total_price DOUBLE PRECISION,
    currency VARCHAR(10) DEFAULT 'USD',
    total_nights INTEGER,
    coupon_code VARCHAR(50),
    discount_percent DOUBLE PRECISION,
    original_total_price DOUBLE PRECISION,
    stay_status VARCHAR(50),
    is_test BOOLEAN DEFAULT false,
    created_by VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE booking_guests (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    guest_name VARCHAR(255),
    guest_email VARCHAR(255),
    guest_phone VARCHAR(50),
    is_primary BOOLEAN DEFAULT false,
    is_test BOOLEAN DEFAULT false,
    created_at TIMESTAMP
);

CREATE TABLE booking_room_guests (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    room_index INTEGER NOT NULL,
    guests TEXT, -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    is_test BOOLEAN DEFAULT false,
    UNIQUE (booking_id, room_index)
);

CREATE TABLE booking_status_history (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    status VARCHAR(50) NOT NULL,
    changed_at TIMESTAMP,
    reason VARCHAR(100),
    changed_by VARCHAR(100),
    is_test BOOLEAN DEFAULT false
);

CREATE TABLE manual_reservations (
    id VARCHAR(24) PRIMARY KEY,
    manual_reservation_id VARCHAR(100) UNIQUE NOT NULL,
    booking_id VARCHAR(100) REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    created_at TIMESTAMP
);

CREATE TABLE hotel_booking_context (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER UNIQUE NOT NULL REFERENCES dim_hotels(prop_id),
    hotel_label VARCHAR(255),
    country INTEGER,
    review_label VARCHAR(255),
    avg_price_label VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE notification_log (
    id VARCHAR(24) PRIMARY KEY,
    notification_type VARCHAR(100) NOT NULL,
    recipient_email VARCHAR(255),
    recipient_name VARCHAR(255),
    booking_id VARCHAR(100) REFERENCES booking_orders(booking_id),
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    status VARCHAR(50),
    error_message TEXT,
    created_at TIMESTAMP
);

-- ============================================================================
-- 7. REVENUE / TARIFAS
-- ============================================================================

CREATE TABLE rate_plans (
    id VARCHAR(24) PRIMARY KEY,
    rate_plan_id VARCHAR(100) UNIQUE NOT NULL,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    name VARCHAR(255),
    base_rate DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT true,
    eligible_roles TEXT -- JSON array
);

CREATE TABLE hotel_rate_calendar (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    rate_plan_id VARCHAR(100) NOT NULL REFERENCES rate_plans(rate_plan_id),
    date DATE NOT NULL,
    rate_amount DOUBLE PRECISION,
    is_closed BOOLEAN DEFAULT false,
    UNIQUE (prop_id, rate_plan_id, date)
);

CREATE TABLE rate_rules (
    id VARCHAR(24) PRIMARY KEY,
    rule_id VARCHAR(100) UNIQUE NOT NULL,
    rate_plan_id VARCHAR(100) REFERENCES rate_plans(rate_plan_id),
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    name VARCHAR(255),
    price_override DOUBLE PRECISION,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE promotion_campaigns (
    id VARCHAR(24) PRIMARY KEY,
    campaign_id VARCHAR(100) UNIQUE NOT NULL,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    name VARCHAR(255),
    description TEXT,
    discount_percent INTEGER,
    start_date DATE,
    end_date DATE,
    is_active BOOLEAN DEFAULT true,
    coupon_count INTEGER DEFAULT 0,
    coupons_used INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE coupon_codes (
    id VARCHAR(24) PRIMARY KEY,
    coupon_code VARCHAR(50) UNIQUE NOT NULL,
    campaign_id VARCHAR(100) NOT NULL REFERENCES promotion_campaigns(campaign_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    discount_percent INTEGER,
    is_active BOOLEAN DEFAULT true,
    used BOOLEAN DEFAULT false,
    used_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- ============================================================================
-- 8. REVIEWS
-- ============================================================================

CREATE TABLE reviews (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) REFERENCES booking_orders(booking_id),
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    user_id VARCHAR(24) REFERENCES users(id),
    rating INTEGER,
    title VARCHAR(255),
    comment TEXT,
    moderation_status VARCHAR(50),
    staff_response TEXT,
    staff_response_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE fact_reviews (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) REFERENCES booking_orders(booking_id),
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    user_id VARCHAR(24) REFERENCES users(id),
    rating INTEGER,
    title VARCHAR(255),
    comment TEXT,
    moderation_status VARCHAR(50),
    staff_response TEXT,
    staff_response_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE review_reports (
    id VARCHAR(24) PRIMARY KEY,
    review_id VARCHAR(24) REFERENCES reviews(id),
    reported_by VARCHAR(100),
    reason TEXT,
    description TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP
);

-- ============================================================================
-- 9. HOUSEKEEPING / MANTENIMIENTO
-- ============================================================================

CREATE TABLE room_status_log (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    hotel_room_id VARCHAR(100),
    room_type_id VARCHAR(100),
    room_label VARCHAR(100),
    room_number VARCHAR(20),
    status VARCHAR(50) NOT NULL,
    dnd BOOLEAN DEFAULT false,
    dnd_updated_at TIMESTAMP,
    note TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (prop_id, hotel_room_id)
);

CREATE TABLE room_status_history (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    room_label VARCHAR(100),
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    note TEXT,
    changed_by VARCHAR(100),
    created_at TIMESTAMP
);

CREATE TABLE housekeeping_tasks (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_label VARCHAR(100),
    task_type VARCHAR(50),
    status VARCHAR(50),
    assigned_to VARCHAR(100),
    priority VARCHAR(20) DEFAULT 'normal',
    note TEXT,
    scheduled_date TIMESTAMP,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE maintenance_tasks (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_label VARCHAR(100),
    task_type VARCHAR(50),
    title VARCHAR(255),
    description TEXT,
    status VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'normal',
    scheduled_date DATE,
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE additional_charges (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    concept VARCHAR(255),
    amount DOUBLE PRECISION,
    quantity INTEGER DEFAULT 1,
    total DOUBLE PRECISION,
    note TEXT,
    created_at TIMESTAMP
);

-- ============================================================================
-- 10. FACTURACION / PAGOS
-- ============================================================================

CREATE TABLE reservation_invoices (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    subtotal DOUBLE PRECISION,
    taxes DOUBLE PRECISION,
    total DOUBLE PRECISION,
    status VARCHAR(50),
    notes TEXT,
    issued_at TIMESTAMP,
    paid_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE fact_reservation_invoices (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    invoice_number VARCHAR(100) UNIQUE NOT NULL,
    subtotal DOUBLE PRECISION,
    taxes DOUBLE PRECISION,
    total DOUBLE PRECISION,
    status VARCHAR(50),
    notes TEXT,
    issued_at TIMESTAMP,
    paid_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE reservation_payments (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    invoice_id VARCHAR(24) REFERENCES reservation_invoices(id),
    amount DOUBLE PRECISION,
    method VARCHAR(50),
    status VARCHAR(50),
    reference VARCHAR(100),
    paid_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE fact_reservation_payments (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    invoice_id VARCHAR(24),
    amount DOUBLE PRECISION,
    method VARCHAR(50),
    status VARCHAR(50),
    reference VARCHAR(100),
    paid_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE guest_folios (
    id VARCHAR(24) PRIMARY KEY,
    folio_number VARCHAR(100) UNIQUE NOT NULL,
    booking_id VARCHAR(100) UNIQUE NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    guest_name VARCHAR(255),
    guest_email VARCHAR(255),
    room_label VARCHAR(100),
    hotel_label VARCHAR(255),
    check_in_date DATE,
    check_out_date DATE,
    status VARCHAR(50),
    total_room DOUBLE PRECISION DEFAULT 0,
    total_charges DOUBLE PRECISION DEFAULT 0,
    total_discounts DOUBLE PRECISION DEFAULT 0,
    total_payments DOUBLE PRECISION DEFAULT 0,
    total_due DOUBLE PRECISION DEFAULT 0,
    postings TEXT, -- JSON array
    posting_count INTEGER DEFAULT 0,
    invoice_id VARCHAR(24),
    created_at TIMESTAMP,
    closed_at TIMESTAMP,
    closed_by VARCHAR(100),
    updated_at TIMESTAMP
);

-- ============================================================================
-- 11. MODULOS ADICIONALES
-- ============================================================================

CREATE TABLE geo_catalog (
    id VARCHAR(24) PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    iso_code VARCHAR(10),
    country_code VARCHAR(10),
    state_code VARCHAR(10),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    UNIQUE (type, code)
);

CREATE TABLE reception_shifts (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    shift_type VARCHAR(50),
    status VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    employee_name VARCHAR(255),
    notes TEXT
);

CREATE TABLE lost_and_found (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    booking_id VARCHAR(100) REFERENCES booking_orders(booking_id),
    status VARCHAR(50),
    description TEXT,
    location_found VARCHAR(255),
    reported_by VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE click_events (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    source VARCHAR(50),
    user_id VARCHAR(100),
    clicked_at TIMESTAMP
);

-- ============================================================================
-- 12. ETL / CONTROL / AUDITORIA
-- ============================================================================

CREATE TABLE search_logs (
    id VARCHAR(24) PRIMARY KEY,
    query VARCHAR(255),
    destination VARCHAR(255),
    country VARCHAR(255),
    min_rating DOUBLE PRECISION,
    page_size INTEGER,
    searched_at TIMESTAMP
);

CREATE TABLE rejected_records (
    id VARCHAR(24) PRIMARY KEY,
    source VARCHAR(100),
    reason TEXT,
    record_data TEXT, -- JSON object
    created_at TIMESTAMP
);

CREATE TABLE etl_executions (
    execution_id VARCHAR(100) PRIMARY KEY,
    phase VARCHAR(20),
    executed_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds DOUBLE PRECISION,
    status VARCHAR(20),
    database VARCHAR(50),
    source TEXT,
    records_processed INTEGER,
    records_rejected INTEGER,
    loaded_collections TEXT, -- JSON object
    final_counts TEXT -- JSON object
);

CREATE TABLE data_quality_reports (
    id VARCHAR(24) PRIMARY KEY,
    execution_id VARCHAR(100),
    phase VARCHAR(20),
    generated_at TIMESTAMP,
    source TEXT,
    source_rows INTEGER,
    valid_fact_records INTEGER,
    invalid_fact_records INTEGER,
    rejected_records INTEGER,
    valid_dimension_records INTEGER,
    invalid_dimension_records INTEGER,
    completeness_score DOUBLE PRECISION,
    dimensions TEXT, -- JSON object
    schema TEXT, -- JSON object
    extract TEXT, -- JSON object
    parquet TEXT -- JSON object
);

CREATE TABLE audit_log (
    id VARCHAR(24) PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    entity_type VARCHAR(50),
    entity_id VARCHAR(100),
    action VARCHAR(50),
    summary TEXT,
    changed_by VARCHAR(100),
    metadata TEXT -- JSON object
);

CREATE TABLE kpi_summary (
    id VARCHAR(24) PRIMARY KEY,
    updated_at TIMESTAMP,
    payload TEXT -- JSON object (contiene quality, overview, counts, charts, etc.)
);

CREATE TABLE system_catalogs (
    id VARCHAR(24) PRIMARY KEY,
    catalog_type VARCHAR(50),
    code VARCHAR(50),
    label VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE system_config (
    id VARCHAR(24) PRIMARY KEY,
    default_commission_pct DOUBLE PRECISION,
    default_iva_pct DOUBLE PRECISION,
    updated_at TIMESTAMP,
    updated_by VARCHAR(100)
);

CREATE TABLE amenity_stock (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    amenity_label VARCHAR(100),
    room_type_id VARCHAR(100),
    quantity INTEGER,
    UNIQUE (prop_id, amenity_label, room_type_id)
);

CREATE TABLE commission_rates (
    id VARCHAR(24) PRIMARY KEY,
    prop_id INTEGER UNIQUE REFERENCES dim_hotels(prop_id),
    commission_pct DOUBLE PRECISION
);

CREATE TABLE tax_rates (
    id VARCHAR(24) PRIMARY KEY,
    country_id VARCHAR(10) UNIQUE,
    country_name VARCHAR(100),
    tax_pct DOUBLE PRECISION
);

-- ============================================================================
-- 13. EXPENSES Y LIBRO MAYOR
-- ============================================================================

CREATE TABLE expense_invoices (
    id VARCHAR(24) PRIMARY KEY,
    vendor_name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    amount DOUBLE PRECISION NOT NULL,
    tax_amount DOUBLE PRECISION DEFAULT 0,
    total DOUBLE PRECISION,
    status VARCHAR(50) DEFAULT 'pending',
    invoice_date DATE,
    due_date DATE,
    approved_by VARCHAR(100),
    approved_at TIMESTAMP,
    notes TEXT,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE expense_categories (
    id VARCHAR(24) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    budget DOUBLE PRECISION DEFAULT 0,
    spent DOUBLE PRECISION DEFAULT 0,
    remaining DOUBLE PRECISION DEFAULT 0,
    created_at TIMESTAMP
);

CREATE TABLE expense_budget (
    id VARCHAR(24) PRIMARY KEY,
    department VARCHAR(100) NOT NULL,
    period VARCHAR(20) NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    spent DOUBLE PRECISION DEFAULT 0,
    remaining DOUBLE PRECISION DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP
);

CREATE TABLE ledger_transactions (
    id VARCHAR(24) PRIMARY KEY,
    tx_date DATE NOT NULL,
    folio_ref VARCHAR(100),
    description TEXT,
    account_code VARCHAR(50) NOT NULL,
    account_name VARCHAR(255),
    debit DOUBLE PRECISION DEFAULT 0,
    credit DOUBLE PRECISION DEFAULT 0,
    balance DOUBLE PRECISION DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    user VARCHAR(100),
    notes TEXT,
    journal_entry_id VARCHAR(100),
    created_at TIMESTAMP
);

CREATE TABLE chart_of_accounts (
    id VARCHAR(24) PRIMARY KEY,
    account_code VARCHAR(50) UNIQUE NOT NULL,
    account_name VARCHAR(255),
    account_type VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- ============================================================================
-- 14. RECURSOS HUMANOS (HR)
-- ============================================================================

CREATE TABLE employees (
    id VARCHAR(24) PRIMARY KEY,
    full_name VARCHAR(255) NOT NULL,
    id_document VARCHAR(100) UNIQUE NOT NULL,
    phone VARCHAR(50),
    email VARCHAR(255),
    address TEXT,
    position VARCHAR(100),
    department VARCHAR(100),
    hire_date DATE,
    salary DOUBLE PRECISION,
    emergency_contact VARCHAR(255),
    emergency_phone VARCHAR(50),
    notes TEXT,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE TABLE employee_departments (
    id VARCHAR(24) PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    head_count INTEGER DEFAULT 0,
    created_at TIMESTAMP
);

CREATE TABLE employee_documents (
    id VARCHAR(24) PRIMARY KEY,
    employee_id VARCHAR(24) NOT NULL REFERENCES employees(id),
    doc_type VARCHAR(50) NOT NULL,
    filename VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP
);

CREATE TABLE employee_shifts (
    id VARCHAR(24) PRIMARY KEY,
    employee_id VARCHAR(24) NOT NULL REFERENCES employees(id),
    date DATE NOT NULL,
    scheduled_start VARCHAR(10),
    scheduled_end VARCHAR(10),
    area VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    actual_check_in TIMESTAMP,
    actual_check_out TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP
);

CREATE TABLE employee_permissions (
    id VARCHAR(24) PRIMARY KEY,
    employee_id VARCHAR(24) NOT NULL REFERENCES employees(id),
    permission_code VARCHAR(100) NOT NULL,
    transferred_from VARCHAR(24),
    created_at TIMESTAMP
);

-- ============================================================================
-- 15. IN-STAY (Mi Estancia)
-- ============================================================================

CREATE TABLE pending_registrations (
    id VARCHAR(24) PRIMARY KEY,
    username VARCHAR(100),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    display_name VARCHAR(255),
    code_hash VARCHAR(64),
    attempts INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE stay_sessions (
    id VARCHAR(24) PRIMARY KEY,
    token VARCHAR(255) UNIQUE NOT NULL,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_label VARCHAR(100),
    guest_name VARCHAR(255),
    check_in DATE,
    check_out DATE,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    active BOOLEAN DEFAULT true,
    deactivated_at TIMESTAMP
);

CREATE TABLE stay_messages (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_label VARCHAR(100),
    sender VARCHAR(20) NOT NULL,
    staff_name VARCHAR(255),
    message TEXT NOT NULL,
    created_at TIMESTAMP,
    read BOOLEAN DEFAULT false
);

CREATE TABLE stay_service_requests (
    id VARCHAR(24) PRIMARY KEY,
    booking_id VARCHAR(100) NOT NULL REFERENCES booking_orders(booking_id),
    prop_id INTEGER NOT NULL REFERENCES dim_hotels(prop_id),
    room_label VARCHAR(100),
    request_type VARCHAR(50) NOT NULL,
    request_type_label VARCHAR(255),
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    status_label VARCHAR(255),
    staff_response TEXT,
    staff_responded_at TIMESTAMP,
    created_at TIMESTAMP,
    resolved_at TIMESTAMP
);

-- ============================================================================
-- 16. ANALITICA ALTERNATIVA
-- ============================================================================

CREATE TABLE fact_hotel_events (
    id BIGSERIAL PRIMARY KEY,
    source_record_id VARCHAR(100),
    srch_id INTEGER NOT NULL,
    date_time TIMESTAMP,
    date_key INTEGER REFERENCES dim_dates(date_key),
    site_id INTEGER REFERENCES dim_sites(site_id),
    visitor_location_country_id INTEGER REFERENCES dim_visitor_countries(visitor_location_country_id),
    visitor_hist_starrating DOUBLE PRECISION,
    visitor_hist_adr_usd DOUBLE PRECISION,
    prop_country_id INTEGER,
    prop_id INTEGER REFERENCES dim_hotels(prop_id),
    prop_starrating INTEGER,
    prop_review_score DOUBLE PRECISION,
    prop_brand_bool BOOLEAN,
    prop_location_score1 DOUBLE PRECISION,
    price_usd DOUBLE PRECISION NOT NULL,
    promotion_flag BOOLEAN REFERENCES dim_promotions(promotion_flag),
    srch_destination_id INTEGER REFERENCES dim_destinations(srch_destination_id),
    srch_length_of_stay INTEGER,
    srch_booking_window INTEGER,
    srch_adults_count INTEGER,
    srch_children_count INTEGER,
    srch_room_count INTEGER,
    click_bool BOOLEAN REFERENCES dim_click_status(click_bool),
    reserva_bool BOOLEAN REFERENCES dim_reservation_status(reserva_bool),
    reservas_brutas_usd DOUBLE PRECISION,
    occupancy_profile_id VARCHAR(50) REFERENCES dim_occupancy_profile(occupancy_profile_id),
    stay_length_category_id VARCHAR(50) REFERENCES dim_stay_length_category(stay_length_category_id),
    booking_window_category_id VARCHAR(50) REFERENCES dim_booking_window_category(booking_window_category_id),
    price_category_id VARCHAR(50) REFERENCES dim_price_category(price_category_id),
    loaded_at TIMESTAMP,
    execution_id VARCHAR(100),
    phase VARCHAR(20)
);
