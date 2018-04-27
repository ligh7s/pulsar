from pulsar import ma
from .models import User
from pulsar.auth.schemas import APIKeySchema


class UserSchema(ma.ModelSchema):
    class Meta:
        model = User
        fields = ('id', 'username', 'invites')


class DetailedUserSchema(ma.ModelSchema):

    class Meta:
        model = User
        fields = ('id', 'username', 'api_keys', 'invites')

    api_keys = ma.Nested(APIKeySchema)


user_schema = UserSchema()
detailed_user_schema = DetailedUserSchema()
multiple_user_schema = UserSchema(many=True)