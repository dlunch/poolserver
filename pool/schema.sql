create table miner (
    id serial not null primary key,

    user_id int not null,
    username varchar(255) not null,
    password varchar(255) not null,
    difficulty int not null,
    created_at timestamp not null,
    updated_at timestamp not null
);

create table round (
    id serial not null primary key,

    height int not null,
    created_at timestamp not null
);

create table share_data (
    id serial not null primary key,

    round_id int not null,
    user_id int null,
    count int not null,
    created_at timestamp not null
);

create table found_blocks (
    id serial not null primary key,

    user_id int not null,
    round_id int not null,
    created_at timestamp not null
);
