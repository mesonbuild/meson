## i18n module now returns gettext targets

`r = i18n.gettext('mydomain')` will now provide access to:
- a list of built .mo files
- the mydomain-pot maintainer target which updates .pot files
- the mydomain-update-po maintainer target which updates .po files
