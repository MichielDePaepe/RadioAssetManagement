from django.db import migrations, models
import django.db.models.deletion


def migrate_sqlite(schema_editor):
    schema_editor.connection.connection.executescript(
        """
        PRAGMA foreign_keys=OFF;

        CREATE TABLE "fireplan_fireplaninventory_new" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "uuid" char(32) NULL UNIQUE,
            "vehicle_alpha_code" varchar(16) NOT NULL,
            "closed_at" datetime NULL,
            "done_by_full_name" varchar(128) NOT NULL,
            "overseen_by_full_name" varchar(128) NOT NULL,
            "root_inventoried_container_uuid" char(32) NULL,
            "synced_at" datetime NOT NULL,
            "vehicle_id" integer NULL REFERENCES "fireplan_vehicle" ("id") DEFERRABLE INITIALLY DEFERRED,
            "vector_id" varchar(50) NULL REFERENCES "fireplan_vector" ("resourceCode") DEFERRABLE INITIALLY DEFERRED
        );

        INSERT INTO "fireplan_fireplaninventory_new" (
            "id",
            "uuid",
            "vehicle_alpha_code",
            "closed_at",
            "done_by_full_name",
            "overseen_by_full_name",
            "root_inventoried_container_uuid",
            "synced_at",
            "vehicle_id",
            "vector_id"
        )
        SELECT
            rowid,
            "uuid",
            "vehicle_alpha_code",
            "closed_at",
            "done_by_full_name",
            "overseen_by_full_name",
            "root_inventoried_container_uuid",
            "synced_at",
            "vehicle_id",
            "vector_id"
        FROM "fireplan_fireplaninventory";

        CREATE TABLE "fireplan_fireplaninventoryradio_new" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "container_uuid" char(32) NULL,
            "item_uuid" char(32) NULL,
            "tracked_item_id" integer NULL,
            "tei" varchar(64) NOT NULL,
            "inventory_id" bigint NOT NULL REFERENCES "fireplan_fireplaninventory_new" ("id") DEFERRABLE INITIALLY DEFERRED,
            "radio_id" bigint NULL REFERENCES "radio_radio" ("TEI") DEFERRABLE INITIALLY DEFERRED,
            CONSTRAINT "uniq_fireplan_inventory_radio_item" UNIQUE ("inventory_id", "item_uuid")
        );

        INSERT INTO "fireplan_fireplaninventoryradio_new" (
            "id",
            "container_uuid",
            "item_uuid",
            "tracked_item_id",
            "tei",
            "inventory_id",
            "radio_id"
        )
        SELECT
            r."id",
            r."container_uuid",
            r."item_uuid",
            r."tracked_item_id",
            r."tei",
            i."id",
            r."radio_id"
        FROM "fireplan_fireplaninventoryradio" r
        INNER JOIN "fireplan_fireplaninventory_new" i ON i."uuid" = r."inventory_id";

        DROP TABLE "fireplan_fireplaninventoryradio";
        DROP TABLE "fireplan_fireplaninventory";
        ALTER TABLE "fireplan_fireplaninventory_new" RENAME TO "fireplan_fireplaninventory";
        ALTER TABLE "fireplan_fireplaninventoryradio_new" RENAME TO "fireplan_fireplaninventoryradio";

        CREATE INDEX "fireplan_fireplaninventory_vehicle_alpha_code_9c761e46" ON "fireplan_fireplaninventory" ("vehicle_alpha_code");
        CREATE INDEX "fireplan_fireplaninventory_closed_at_36023304" ON "fireplan_fireplaninventory" ("closed_at");
        CREATE INDEX "fireplan_fireplaninventory_root_inventoried_container_uuid_20f13d01" ON "fireplan_fireplaninventory" ("root_inventoried_container_uuid");
        CREATE INDEX "fireplan_fireplaninventory_vehicle_id_c7016e62" ON "fireplan_fireplaninventory" ("vehicle_id");
        CREATE INDEX "fireplan_fireplaninventory_vector_id_60378ae2" ON "fireplan_fireplaninventory" ("vector_id");
        CREATE INDEX "fireplan_fireplaninventoryradio_container_uuid_51da1745" ON "fireplan_fireplaninventoryradio" ("container_uuid");
        CREATE INDEX "fireplan_fireplaninventoryradio_item_uuid_a063d130" ON "fireplan_fireplaninventoryradio" ("item_uuid");
        CREATE INDEX "fireplan_fireplaninventoryradio_tracked_item_id_ec20bbf0" ON "fireplan_fireplaninventoryradio" ("tracked_item_id");
        CREATE INDEX "fireplan_fireplaninventoryradio_tei_b204df50" ON "fireplan_fireplaninventoryradio" ("tei");
        CREATE INDEX "fireplan_fireplaninventoryradio_inventory_id_25d979ee" ON "fireplan_fireplaninventoryradio" ("inventory_id");
        CREATE INDEX "fireplan_fireplaninventoryradio_radio_id_c4952024" ON "fireplan_fireplaninventoryradio" ("radio_id");

        PRAGMA foreign_keys=ON;
        """
    )


def migrate_postgresql(schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute(
        """
        CREATE SEQUENCE IF NOT EXISTS fireplan_fireplaninventory_id_seq;
        ALTER TABLE fireplan_fireplaninventory ADD COLUMN id bigint;
        UPDATE fireplan_fireplaninventory
           SET id = nextval('fireplan_fireplaninventory_id_seq')
         WHERE id IS NULL;
        ALTER TABLE fireplan_fireplaninventory
            ALTER COLUMN id SET DEFAULT nextval('fireplan_fireplaninventory_id_seq'),
            ALTER COLUMN id SET NOT NULL;
        ALTER SEQUENCE fireplan_fireplaninventory_id_seq OWNED BY fireplan_fireplaninventory.id;

        ALTER TABLE fireplan_fireplaninventoryradio ADD COLUMN inventory_new_id bigint;
        UPDATE fireplan_fireplaninventoryradio r
           SET inventory_new_id = i.id
          FROM fireplan_fireplaninventory i
         WHERE r.inventory_id = i.uuid;
        ALTER TABLE fireplan_fireplaninventoryradio ALTER COLUMN inventory_new_id SET NOT NULL;

        DO $$
        DECLARE constraint_name text;
        BEGIN
          SELECT conname INTO constraint_name
          FROM pg_constraint
          WHERE conrelid = 'fireplan_fireplaninventoryradio'::regclass
            AND contype = 'f'
            AND conkey = ARRAY[
              (SELECT attnum FROM pg_attribute
               WHERE attrelid = 'fireplan_fireplaninventoryradio'::regclass
                 AND attname = 'inventory_id')
            ];
          IF constraint_name IS NOT NULL THEN
            EXECUTE format('ALTER TABLE fireplan_fireplaninventoryradio DROP CONSTRAINT %I', constraint_name);
          END IF;
        END $$;

        ALTER TABLE fireplan_fireplaninventoryradio DROP CONSTRAINT IF EXISTS uniq_fireplan_inventory_radio_item;

        DO $$
        DECLARE constraint_name text;
        BEGIN
          SELECT conname INTO constraint_name
          FROM pg_constraint
          WHERE conrelid = 'fireplan_fireplaninventory'::regclass
            AND contype = 'p';
          IF constraint_name IS NOT NULL THEN
            EXECUTE format('ALTER TABLE fireplan_fireplaninventory DROP CONSTRAINT %I', constraint_name);
          END IF;
        END $$;

        ALTER TABLE fireplan_fireplaninventory
            ALTER COLUMN uuid DROP NOT NULL,
            ADD CONSTRAINT fireplan_fireplaninventory_pkey PRIMARY KEY (id),
            ADD CONSTRAINT fireplan_fireplaninventory_uuid_key UNIQUE (uuid);

        ALTER TABLE fireplan_fireplaninventoryradio DROP COLUMN inventory_id;
        ALTER TABLE fireplan_fireplaninventoryradio RENAME COLUMN inventory_new_id TO inventory_id;
        ALTER TABLE fireplan_fireplaninventoryradio
            ALTER COLUMN container_uuid DROP NOT NULL,
            ALTER COLUMN item_uuid DROP NOT NULL,
            ADD CONSTRAINT fireplan_fireplaninventoryradio_inventory_id_fk
                FOREIGN KEY (inventory_id)
                REFERENCES fireplan_fireplaninventory(id)
                DEFERRABLE INITIALLY DEFERRED,
            ADD CONSTRAINT uniq_fireplan_inventory_radio_item
                UNIQUE (inventory_id, item_uuid);
        """
    )


def migrate_inventory_keys(apps, schema_editor):
    if schema_editor.connection.vendor == "sqlite":
        migrate_sqlite(schema_editor)
    elif schema_editor.connection.vendor == "postgresql":
        migrate_postgresql(schema_editor)
    else:
        raise RuntimeError("Unsupported database backend for Fireplan inventory key migration.")


class Migration(migrations.Migration):

    dependencies = [
        ("fireplan", "0012_link_short_fireplan_inventory_teis"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(migrate_inventory_keys, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="fireplaninventory",
                    name="id",
                    field=models.BigAutoField(primary_key=True, serialize=False),
                ),
                migrations.AlterField(
                    model_name="fireplaninventory",
                    name="uuid",
                    field=models.UUIDField(blank=True, null=True, unique=True),
                ),
                migrations.AlterField(
                    model_name="fireplaninventoryradio",
                    name="container_uuid",
                    field=models.UUIDField(blank=True, db_index=True, null=True),
                ),
                migrations.AlterField(
                    model_name="fireplaninventoryradio",
                    name="item_uuid",
                    field=models.UUIDField(blank=True, db_index=True, null=True),
                ),
                migrations.AlterField(
                    model_name="fireplaninventoryradio",
                    name="inventory",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="radios",
                        to="fireplan.fireplaninventory",
                    ),
                ),
            ],
        ),
    ]
