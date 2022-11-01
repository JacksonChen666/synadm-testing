# -*- coding: utf-8 -*-
# synadm
# Copyright (C) 2022 Philip (a-0)
#
# synadm is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# synadm is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""server notice-related CLI commands
"""

import re
import click

from synadm import cli


@cli.root.group()
def notice():
    """ Send server notices to local users
    """


@notice.command(name="send")
@click.option(
    "--from-file", "-f", default=False, show_default=True, is_flag=True,
    help="""Interpret arguments as file paths instead of notice content and
    read content from those files.""")
@click.option(
    "--paginate", "-p", type=int, default=100, show_default=True,
    metavar="PAGINATE", help="""The send command retrieves "pages" of users
    from the homeserver, filters them and sends out the notices, before
    retrieving the next page. PAGINATE sets how many users are in each of these
    "pages". It is a performance setting and may be useful for servers with a
    large amount of users.""")
@click.option(
    "--to-regex", "-r", default=False, show_default=True, is_flag=True,
    help="Interpret TO as regular expression.")
@click.option(
    "--preview-length", "-l", type=int, default=10, show_default=True,
    metavar="LENGTH", help="""Length of the displayed list of matched
    recipients shown in the confirmation prompt. Does not impact sending
    behavior. Is ignored when global --non-interactive flag is given.""")
@click.argument("to", type=str, default=None)
@click.argument("plain", type=str, default=None)
@click.argument("formatted", type=str, default=None, required=False)
@click.pass_obj
def notice_send_cmd(helper, from_file, paginate, to_regex, preview_length,
                    to, plain, formatted):
    """Send server notices to local users.

    TO - localpart or full matrix ID of the notice receiver. If --to-regex is
        set this will be interpreted as regular expression.

    PLAIN - plain text content of the notice.

    FORMATTED - Formatted content of the notice. If omitted, PLAIN will be
        used.
    """
    def confirm_prompt():
        if helper.batch:
            return True
        prompt = "Recipients:\n"
        if not to_regex:
            prompt += " - " + to + "\n"
        else:
            # Build and print a list of receivers matching the regex
            ctr, next_token = 0, 0
            # Outer loop: If fetching >1 pages of users is required
            while ctr < preview_length:
                batch = helper.api.user_list(
                    next_token, paginate, True, False, "", "")
                if "users" not in batch:
                    break
                batch_mxids = [user['name'] for user in batch["users"]]
                # Match every matrix ID of this batch
                for mxid in batch_mxids:
                    if re.match(to, mxid):
                        if ctr < preview_length:
                            prompt += " - " + mxid + "\n"
                            ctr += 1
                        else:
                            prompt += " - ...\n"
                            break
                if "next_token" not in batch:
                    break
                next_token = batch["next_token"]
            if ctr == 0:
                prompt += "(no recipient matched)\n"
        prompt += f"\nPlaintext message:\n---\n{plain_content}\n---"
        prompt += f"\nFormatted message:\n---\n{formatted_content}\n---"
        prompt += "\nSend now?"
        return click.confirm(prompt)

    if from_file:
        with open(plain, "r") as plain_file:
            plain_content = plain_file.read()
        if formatted:
            with open(formatted, "r") as formatted_file:
                formatted_content = formatted_file.read()
        else:
            formatted_content = plain_content
    else:
        plain_content = plain
        formatted_content = formatted if formatted else plain_content

    if to_regex:
        if "users" not in helper.api.user_list(0, 100, True, False, "", ""):
            return
        if not confirm_prompt():
            return
    else:
        to = helper.generate_mxid(to)
        if to is None:
            print("The recipient you specified is invalid.")
            return
        if not confirm_prompt():
            return

    outputs = helper.api.notice_send(to, plain_content, formatted_content,
                                     paginate, to_regex)
    helper.output(outputs)