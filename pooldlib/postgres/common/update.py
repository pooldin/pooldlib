class FieldUpdateMixin(object):
    def update_fields(self, fields, nullable=False):
        if hasattr(fields, 'items'):
            fields = fields.items()

        for field, value in fields:
            self.update_field(field, value, nullable=nullable)

    def update_field(self, field, new_value, nullable=False):
        if new_value is None and not nullable:
            return False

        current_value = getattr(self, field)
        is_equal = self.is_field_equal(field, current_value, new_value)

        if not is_equal:
            setattr(self, field, new_value)
            return True

        return False

    def is_field_equal(self, field, current_value, new_value):
        return current_value == new_value
