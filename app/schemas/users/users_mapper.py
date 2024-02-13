from app.models.admindb import ApplicationUser, Role
from app.schemas.users.users_response import ApplicationUserRoleSchema, ApplicationUserSchema


class ApplicationUserMapper:
    @staticmethod
    def map_to_application_user_response(user: ApplicationUser):
        roles = [
            ApplicationUserMapper.map_to_application_user_role_response(user_role.role)
            for user_role in user.user_roles
        ]
        return ApplicationUserSchema(
            id=user.id.hex,
            azure_object_id=user.azure_object_id,
            first_name=user.first_name,
            last_name=user.last_name,
            roles=roles,
        )

    @staticmethod
    def map_to_application_user_role_response(role: Role):
        return ApplicationUserRoleSchema(id=role.id.hex, name=role.name)
