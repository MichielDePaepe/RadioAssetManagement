from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'

    def ready(self):
        from polymorphic.deletion import PolymorphicGuard

        if getattr(PolymorphicGuard, "_ram_equality_patch", False):
            return

        def __eq__(self, other):
            return self.action == getattr(other, "action", other)

        def __hash__(self):
            return hash(self.action)

        PolymorphicGuard.__eq__ = __eq__
        PolymorphicGuard.__hash__ = __hash__
        PolymorphicGuard._ram_equality_patch = True
