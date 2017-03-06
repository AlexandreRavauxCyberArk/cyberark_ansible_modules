#!/usr/bin/python
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#


ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'committer',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: cyberark_user
short_description: "Module for CyberArk User Management using Privileged Account
                    Security Web Services SDK"
author: "Edward Nunez (@enunez-cyberark)"
version_added: "2.3"
description:
    - "CyberArk User Management using PAS Web Services SDK.
       It currently supports the following actions: Get User Details, Add User,
       Update User, Delete User.
       It requires C(cyberark_session) parameter to be passed as a current
       session established by logon/logoff using cyberark_authentication.module"


options:
    username:
        required: True
        description:
            - The name of the user who will be queried (for details), added, updated or deleted.
    state:
        default: details
        choices: ['details', 'present', 'update', 'absent']
        description:
            - Specifies the state (defining the action to follow) needed for the user.
              'details' for query user details, 'present' for create user,
              'update' for update user (even the password), 'delete' for delete user.
    cyberark_session:
        required: True
        description:
            - Dictionary set by a CyberArk authentication containing the different values to perform actions on a logged-on CyberArk session.
    initial_password:
        description:
            - The password that the new user will use to log on the first time. This password must meet the password policy requirements.
              this parameter is required when state is 'present' -- Add User.
    new_password:
        description:
            - The user's updated password. Make sure that this password meets the password policy requirements.
    email:
        description:
            - The user's email address.
    first_name:
        description:
            - The user's first name.
    last_name:
        description:
            - The user's last name.
    change_password_on_the_next_logon:
        default: false
        description:
            - Whether or not the user must change their password in their next logon.
              Valid values = true/false.
    expiry_date:
        description:
            - The date and time when the user's account will expire and become disabled.
    user_type_name:
        default: EPVUser
        description:
            - The type of user.
    disabled:
        default: false
        description:
            - Whether or not the user will be disabled. Valid values = true/false.
    location:
        description:
            - The Vault Location for the user.
'''

EXAMPLES = '''
- name: Logon to CyberArk Vault using PAS Web Services SDK
  cyberark_authentication:
    api_base_url: "https://components.cyberark.local"
    use_shared_logon_authentication: true

- name: Get Users Details
  cyberark_user:
    username: "Username"
    state: details
    cyberark_session: "{{ cyberark_session }}"

- name: Create user
  cyberark_user:
    username: "username"
    initial_password: "password"
    user_type_name: "EPVUser"
    change_password_on_the_next_logon: false
    state: present
    cyberark_session: "{{ cyberark_session }}"

- name: Reset user credential
  cyberark_user:
    username: "Username"
    new_password: "password"
    disabled: false
    state: update
    cyberark_session: "{{ cyberark_session }}"

- name: Logoff from CyberArk Vault
  cyberark_authentication:
    state: absent
    cyberark_session: "{{ cyberark_session }}"
'''

RETURN = '''
cyberark_user:
    description: Dictionary containing result property.
    returned: success
    type: dictionary
    contains:
        result:
            description: properties of the result user (either added/updated).
            type: dictionary
            sample: {
                        "AgentUser": false,
                        "Disabled": false,
                        "Email": "",
                        "Expired": false,
                        "ExpiryDate": null,
                        "FirstName": "",
                        "LastName": "",
                        "Location": "Applications",
                        "Source": "Internal",
                        "Suspended": false,
                        "username": "Prov_centos01",
                        "UserTypeName": "AppProvider"
                    }
status_code:
    description: Result HTTP Status code
    returned: success
    type: int
    sample: 200
'''

from ansible.module_utils.basic import AnsibleModule 
from ansible.module_utils.urls import open_url
import traceback
import sys
import json


def userDetails(module):

    # Get username from module parameters, and api base url
    # along with validate_certs from the cyberark_session established
    username = module.params["username"]
    cyberark_session = module.params["cyberark_session"]
    api_base_url = cyberark_session["api_base_url"]
    validate_certs = cyberark_session["validate_certs"]

    # Prepare result, end_point, and headers
    result = {}
    end_point = "/PasswordVault/WebServices/PIMServices.svc/Users/{0}".format(
        username)
    headers = {'Content-Type': 'application/json'}
    headers["Authorization"] = cyberark_session["token"]

    try:

        response = open_url(
            api_base_url + end_point,
            method="GET",
            headers=headers,
            validate_certs=validate_certs)
        result = {"result": json.loads(response.read())}

        return (False, result, response.getcode())

    except Exception:

        t, e = sys.exc_info()[:2]
        module.fail_json(
            msg=str(e),
            exception=traceback.format_exc(),
            status_code=e.code)


def userAddOrUpdate(module, HTTPMethod):

    # Get username from module parameters, and api base url
    # along with validate_certs from the cyberark_session established
    username = module.params["username"]
    cyberark_session = module.params["cyberark_session"]
    api_base_url = cyberark_session["api_base_url"]
    validate_certs = cyberark_session["validate_certs"]

    if module.check_mode:
        # return if case of check_mode
        module.exit_json(change=False)

    # Prepare result, paylod, and headers
    result = {}
    payload = {}
    headers = {'Content-Type': 'application/json',
               "Authorization": cyberark_session["token"]}

    # end_point and payload sets different depending on POST/PUT
    # for POST -- create -- payload contains username
    # for PUT -- update -- username is part of the endpoint
    if HTTPMethod == "POST":
        end_point = "/PasswordVault/WebServices/PIMServices.svc/Users"
        payload["username"] = username
    elif HTTPMethod == "PUT":
        end_point = "/PasswordVault/WebServices/PIMServices.svc/Users/{0}"
        end_point = end_point.format(username)


    # --- Optionally populate payload based on parameters passed ---
    if "initial_password" in module.params:
        payload["InitialPassword"] = module.params["initial_password"]

    if "new_password" in module.params:
        payload["NewPassword"] = module.params["new_password"]

    if "email" in module.params:
        payload["Email"] = module.params["email"]

    if "first_name" in module.params:
        payload["FirstName"] = module.params["first_name"]

    if "last_name" in module.params:
        payload["LastName"] = module.params["last_name"]

    if "change_password_on_the_next_logon" in module.params:
        if module.params["change_password_on_the_next_logon"]:
            payload["ChangePasswordOnTheNextLogon"] = "true"
        else:
            payload["ChangePasswordOnTheNextLogon"] = "false"

    if "expiry_date" in module.params:
        payload["ExpiryDate"] = module.params["expiry_date"]

    if "user_type_name" in module.params:
        payload["UserTypeName"] = module.params["user_type_name"]

    if "disabled" in module.params:
        if module.params["disabled"]:
            payload["Disabled"] = "true"
        else:
            payload["Disabled"] = "false"

    if "location" in module.params:
        payload["Location"] = module.params["location"]
    # --------------------------------------------------------------

    try:

        response = open_url(
            api_base_url + end_point,
            method=HTTPMethod,
            headers=headers,
            data=json.dumps(payload),
            validate_certs=validate_certs)

        result = {"result": json.loads(response.read())}

        return (True, result, response.getcode())

    except Exception:

        t, e = sys.exc_info()[:2]
        module.fail_json(
            msg=str(e),
            exception=traceback.format_exc(),
            status_code=e.code)


def userDelete(module):

    # Get username from module parameters, and api base url
    # along with validate_certs from the cyberark_session established
    username = module.params["username"]
    cyberark_session = module.params["cyberark_session"]
    api_base_url = cyberark_session["api_base_url"]
    validate_certs = cyberark_session["validate_certs"]

    if module.check_mode:
        # return if case of check_mode
        module.exit_json(change=False)

    # Prepare result, end_point, and headers
    result = {}
    end_point = "/PasswordVault/WebServices/PIMServices.svc/Users/{0}".format(
        username)

    headers = {'Content-Type': 'application/json'}
    headers["Authorization"] = cyberark_session["token"]

    try:

        response = open_url(
            api_base_url + end_point,
            method="DELETE",
            headers=headers,
            validate_certs=validate_certs)

        result = {"result": {}}

        return (True, result, response.getcode())

    except Exception:

        t, e = sys.exc_info()[:2]
        module.fail_json(
            msg=str(e),
            exception=traceback.format_exc(),
            status_code=e.code)


def main():

    fields = {
        "username": {"required": True, "type": "str"},
        "state": {"type": "str",
                  "choices": ["details", "present", "update", "absent"],
                  "default": "details"},
        "cyberark_session": {"required": True, "type": "dict"},
        "initial_password": {"type": "str"},
        "new_password": {"type": "str"},
        "email": {"type": "str"},
        "first_name": {"type": "str"},
        "last_name": {"type": "str"},
        "change_password_on_the_next_logon": {"type": "bool"},
        "expiry_date": {"type": "str"},
        "user_type_name": {"type": "str"},
        "disabled": {"type": "bool"},
        "location": {"type": "str"},
    }

    required_if = [
        ("state", "present", ["initial_password"]),
    ]

    module = AnsibleModule(argument_spec=fields, required_if=required_if)

    state = module.params["state"]

    changed = False
    result = {}

    if (state == "details"):
        (changed, result, status_code) = userDetails(module)
    elif (state == "present"):
        (changed, result, status_code) = userAddOrUpdate(module, "POST")
    elif (state == "update"):
        (changed, result, status_code) = userAddOrUpdate(module, "PUT")
    elif (state == "absent"):
        (changed, result, status_code) = userDelete(module)

    module.exit_json(
        changed=changed,
        cyberark_user=result,
        status_code=status_code)


if __name__ == '__main__':
    main()
