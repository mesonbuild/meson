## i18n.merge_file() now fully supports variable substitutions defined in custom_target()

Filename substitutions like @BASENAME@ and @PLAINNAME@ were previously accepted but the name of the build target wasn't altered leading to colliding target names when using the substitution twice.
i18n.merge_file() now behaves as custom_target() in this regard.
