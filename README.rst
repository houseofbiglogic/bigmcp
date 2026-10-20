=========================
BigMCP — Odoo MCP Server
=========================

**English** | `Türkçe <README.tr.rst>`_

    The bridge that opens your Odoo to AI assistants such as Claude. The
    assistant discovers the models and fields in Odoo by itself; it searches
    and reads records and — as far as you allow — creates or updates them.
    Every operation runs with the connected user's **own Odoo access rights**:
    whatever the user cannot see, the assistant cannot see either.

- **Technical name:** ``bigmcp``
- **Version:** ``19.0.2.0.1`` (Odoo 19)
- **Dependencies:** ``api_doc`` (ships with Odoo)
- **License:** LGPL-3
- **Author:** BigLogic — https://biglogic.tech

.. contents::
   :local:
   :depth: 2

----

1. What Is MCP and What Does This Module Do?
============================================

**MCP (Model Context Protocol)** is a common language that lets AI assistants
connect to external systems. Just as a printer driver lets every program print
to the same printer, MCP lets Claude Desktop, Claude Code or any other
MCP-capable assistant connect to the same Odoo.

BigMCP opens such a connection point at the ``/mcp`` address of your Odoo. When
an assistant connects it sees five generic tools:

===================  ==========================================================
Tool                 What it does
===================  ==========================================================
``list_models``      Lists the models the user can see (Customer, Sales
                     Order, Invoice…) grouped by module.
``describe_model``   Shows the fields and methods of a model together with the
                     MCP notes written for it.
``describe_method``  Explains what a single method does and its parameters.
``search_read``      Searches and reads records (total count + one page).
``call_method``      Calls a method: creating, updating, deleting records,
                     confirming orders — the operations that **change data**.
===================  ==========================================================

So when you ask "What is the total of the invoices issued this month to
customers in Istanbul?", the assistant first finds the invoice model, inspects
its fields and then builds the right query itself. No tool has to be written
for each workflow.

There are three things for you to do:

1. Install the module and give users the **MCP role**.
2. Generate an **API key** for each user and register it with the assistant.
3. (Optional but recommended) Teach the assistant your company's rules with
   **MCP notes** (see section 5).

----

2. Installation
===============

2.1 Prerequisites
-----------------

- Odoo 19.
- An Odoo address reachable from where the assistant runs
  (e.g. ``https://odoo.yourcompany.com``). For cloud assistants such as
  claude.ai this address must be reachable from the internet; with Claude
  Desktop or Claude Code you can also connect to an Odoo on your own network.
- **HTTPS** is strongly recommended: the API key travels with every request.

2.2 Installing the module
-------------------------

1. Copy the ``bigmcp`` folder into Odoo's addons path.
2. Restart the Odoo server.
3. Activate developer mode (**Settings > Activate the developer mode**) and
   click **Apps > Update Apps List**.
4. Search for **BigMCP** in Apps and click **Activate**.

The ``api_doc`` module (Odoo's own API documentation module) is enabled
automatically alongside it.

2.3 Giving a user the MCP role
------------------------------

Every user who will connect through an assistant needs the MCP role; a user
without it cannot connect even with a valid key.

1. Open **Settings > Users & Companies > Users**.
2. On the user form, pick the **MCP Role** under the **MCP Server** heading:

   ===============  ==============================================================
   Role             Rights
   ===============  ==============================================================
   *(empty)*        Cannot connect through MCP.
   **MCP User**     Can connect to ``/mcp`` with an API key. Odoo access
                    rights apply unchanged to every call.
   **MCP Admin**    Everything an MCP User can do, plus writing and editing
                    the **MCP notes**.
   ===============  ==============================================================

3. Save.

Administrators with full access to the **Settings** app become **MCP Admin**
automatically; nothing else is needed for them.

.. note::

   The MCP role does **not** grant any new data access. Whatever records the
   user can see and edit in the Odoo interface, the assistant can see and edit
   exactly those. That is why the safest approach is to connect the assistant
   to a user account with just the rights it really needs rather than a
   broadly privileged administrator account.

2.4 Generating an API key
-------------------------

An API key is a password that lets the assistant tell Odoo "I am this user".
Each user generates their own key from their own profile:

1. Click your user name at the top right and open **Preferences**
   (*My Profile*).
2. Switch to the **Security** tab.
3. Click **Add API Key**; Odoo asks for your password again first.
4. Enter a **description** (e.g. ``Claude Desktop``) and pick a **duration**.
   When the duration expires the key stops working by itself; just generate a
   new one. Only administrators can create keys that never expire.
5. Odoo shows the key **only once**. Copy it and keep it somewhere safe; it
   cannot be displayed again once the window is closed.

If you lose the key or suspect it has been compromised, delete it on the same
screen and generate a new one.

.. warning::

   An API key is as valuable as your password. Do not share it by e-mail or
   chat; enter it only in the settings of the assistant you connect.

2.5 Connecting the assistant to Odoo
------------------------------------

The assistant needs three pieces of information:

=================  ============================================================
Item               Value
=================  ============================================================
Server address     ``https://odoo.yourcompany.com/mcp``
Transport          Streamable HTTP (some clients just say "HTTP")
Authentication     the ``Authorization: Bearer <your API key>`` header
=================  ============================================================

For **Claude Code** (terminal) a single command is enough::

    claude mcp add --transport http odoo https://odoo.yourcompany.com/mcp \
        --header "Authorization: Bearer YOUR_API_KEY"

For **Claude Desktop** add the block below to ``claude_desktop_config.json``
(Settings > Developer > Edit Config). Node.js must be installed on the
computer::

    {
      "mcpServers": {
        "odoo": {
          "command": "npx",
          "args": [
            "-y", "mcp-remote",
            "https://odoo.yourcompany.com/mcp",
            "--header", "Authorization:${ODOO_AUTH}"
          ],
          "env": {
            "ODOO_AUTH": "Bearer YOUR_API_KEY"
          }
        }
      }
    }

Save the file and fully quit and reopen Claude Desktop. The tools menu of the
chat screen should show a server named ``odoo`` with five tools.

If you use another MCP client, enter the three items above in that client's
"remote MCP server" screen. The client must be able to send a custom
**Authorization** header; clients that only support OAuth cannot connect to
BigMCP directly.

2.6 Testing the connection
--------------------------

To try the connection before setting up an assistant, from a terminal::

    curl -X POST https://odoo.yourcompany.com/mcp \
      -H "Authorization: Bearer YOUR_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'

If all is well the answer is ``{"jsonrpc": "2.0", "id": 1, "result": {}}``.
See section 7 for possible errors.

On the assistant side, good first questions are:

- "Which modules are installed in Odoo? List the sales-related models."
- "Show the 5 most recently created customers with their name and city."
- "What is the total amount of the sales orders confirmed this month?"

2.7 Supported MCP versions
--------------------------

With the 2026-07-28 revision the MCP protocol moved to a handshake-free model
in which every request carries its own version. BigMCP serves both models at
the same address; whichever one the connecting client speaks is the one it
gets:

=======================================  ================================================
Client                                   Outcome
=======================================  ================================================
2026-07-28 and later (modern)            Works. Version and capabilities are fetched
                                         with ``server/discover``; every request is
                                         validated on its own.
2025-11-25, 2025-06-18, 2025-03-26       Works. The ``initialize`` handshake is
(handshake based)                        performed and the version the client asked
                                         for is echoed back.
Clients that try both (dual-era)         Works. The client tries the modern request
                                         first and succeeds; no fallback is needed.
=======================================  ================================================

There is nothing for you to do as a user; the choice is settled between client
and server automatically.

----

3. Settings
===========

The **Settings > BigMCP** page holds three settings (listed in the left menu
with the module's icon; only users with the **MCP Admin** role see it):

- **MCP Result Limit (tokens)** — the largest size of a single answer
  (3.1–3.4).
- **MCP Cache Duration (minutes)** — how long a client may reuse the tool
  list and the global notes before asking again (3.5).
- **MCP Allowed Origins** — which websites may connect from a browser (3.6).

3.1 What is the result limit?
-----------------------------

Every time the assistant asks Odoo something (a search, a model description,
a method call) Odoo returns an answer text. This setting decides **how large a
single answer may be at most**. The unit is the "token", the unit AI models use
to measure text; roughly **1 token ≈ 3 characters**. The default is
**25,000 tokens**, i.e. an answer of about 75,000 characters. That comfortably
fits a list of 80 records with a few fields, but not a request like "fetch all
orders with all their fields".

3.2 Why is there a limit?
-------------------------

The assistant has a "working memory" and every answer from Odoo is written
into it. As the conversation goes on the assistant re-reads that memory at
every step. Hence:

- **Cost:** a large answer is billed not only when it arrives but again with
  every later message of the conversation. One careless query makes the whole
  conversation expensive.
- **Capacity:** the memory has a ceiling. A very large answer that exceeds it
  makes the assistant fail or forget the beginning of the conversation.
- **Quality:** the assistant struggles to find what it needs among tens of
  thousands of lines; a narrower query gives a faster and more accurate answer.

The limit is a seat belt that steers the assistant towards small, targeted
queries.

3.3 What happens when the limit is exceeded?
--------------------------------------------

1. The operation **runs completely** in Odoo; only the answer text sent to the
   assistant is cut. If a record creation or confirmation call was cut, the
   record was still created or confirmed.
2. The assistant receives the first part of the answer followed by a warning
   to this effect: *"The result is about X tokens, only the first 25,000 are
   shown. The call itself completed, do not repeat it as is: ask for fewer
   fields or fewer records."*
3. The assistant understands the warning and usually builds a narrower query
   by itself: fewer fields, a smaller page, or grouping tools instead of a
   record list for counts and totals.

If you see "result truncated" in a conversation, do not worry; the assistant
usually reaches the right answer on its second attempt.

3.4 Which value to choose?
--------------------------

For most installations **the default is fine**; you need not touch the
setting. Cases where you may consider changing it:

=========================================  ================================================
Situation                                  Suggestion
=========================================  ================================================
Assistant cost feels high, many users.     Lower the value to **10,000–15,000**. The
                                           assistant narrows more often but every
                                           conversation gets cheaper.
Wide reports (hundreds of rows, many       Raise the value to **40,000–50,000**. Take
columns) get truncated often.              care not to exceed the memory ceiling of the
                                           model you use.
One particular query gets truncated,       Instead of changing the limit, tell the
the others are fine.                       assistant to narrow the request ("only name
                                           and amount", "show the first 50 records").
=========================================  ================================================

Leaving the field empty or entering ``0`` removes the setting; the module
returns to the default of 25,000 tokens. A change takes effect as soon as it
is saved; no server restart and no reconnection of the assistant is needed.

3.5 Cache duration (MCP Cache Duration)
---------------------------------------

The assistant client asks "which tools exist, what are the server
instructions?" in every conversation, sometimes with every message. Those
answers rarely change, so BigMCP tells the client "keep this answer for so
many minutes, do not ask again". The default is **10 minutes**.

The duration affects only two things: the tool list (which never changes) and
the **global MCP notes** (which change whenever an administrator edits them).
So a new global note reaches the assistant with at most this delay. Model and
method notes are not affected; they go out fresh with every inspection.

- If you edit notes often and want to see the effect at once, shorten the
  duration (e.g. 1).
- If notes rarely change and you want to reduce client traffic, lengthen it
  (e.g. 60).
- Leaving the field empty or entering ``0`` restores the default of 10
  minutes; there is no way to switch caching off entirely, 1 minute is the
  shortest practical value.

The duration is only used by clients of 2026-07-28 and later; older clients do
not receive it and keep asking every time, as they do today.

3.6 Allowed origins (MCP Allowed Origins)
-----------------------------------------

A web page can send requests to the ``/mcp`` address through the user's
browser; the browser attaches the page's address (**Origin**) to such a
request. The MCP security rule expects the server to check this address and
reject (``403``) requests from unknown sites, so that a malicious site cannot
reach your Odoo through the session in your browser. BigMCP keeps this check
**off by default** and leaves the decision to you:

- **Star (``*``, default):** every site is accepted; the check is effectively
  off. Leaving the field empty means the same.
- **Address list:** comma separated sites, e.g.
  ``https://claude.ai, https://app.yourcompany.com``. Only the listed sites and
  Odoo's own address are accepted. To restrict browser access to Odoo's own
  address alone, put just that address in the list.

Claude Desktop, Claude Code and server-to-server connectors do not send an
Origin header; they are never affected by this setting. If you switch the
check on (by entering an address list), remember to add the addresses of the
browser-based MCP clients you use; otherwise they get ``403``.

----

4. What Can the Assistant Do in Odoo?
=====================================

Within the rights of the connected user, the assistant can:

- **Read:** search, list, count, group and sum records (e.g. revenue per
  customer, stock per product).
- **Write:** create and update records (a new customer, a quotation line, a
  note).
- **Run workflows:** call the methods behind Odoo's buttons, such as
  confirming a quotation, validating an invoice or completing a transfer.
- **Delete:** if the user can delete in Odoo, so can the assistant.

The data-changing tool (``call_method``) is flagged to the assistant as
"potentially destructive"; Claude clients usually ask for confirmation before
such calls. The real safeguard, however, is the user's Odoo access rights (see
section 6).

Archived records are left out of searches unless you explicitly ask for them.
Image and file fields come back as their size rather than their content, so
large files do not weigh the assistant down.

----

5. MCP Notes
============

5.1 What is a note and why is it needed?
----------------------------------------

The assistant discovers Odoo's technical structure by itself, but it cannot
know **your** company's rules: which customer tag you mean by "dealer", why
orders must not be cancelled, what a field really stands for. An **MCP note**
is the way to pass that knowledge on: a short explanation you write in Odoo
that is shown to the assistant automatically when it looks at the related
subject.

Think of the notes as a short "company handbook" written for the AI. No code
is needed; plain sentences are enough.

5.2 The three scopes
--------------------

Who sees a note and when is decided by whether the **Model** and **Method**
fields are filled in:

======================  ==========================================================
Scope                   When it is shown
======================  ==========================================================
**Global**              Model empty. Shown as soon as the assistant connects,
(no model)              at the start of every conversation. For company-wide
                        rules and terms.
**Model note**          Model filled, method empty. Shown when the assistant
                        inspects that model (``describe_model``). For field
                        meanings, state codes, "don't do this" warnings.
**Method note**         Model and method filled. Shown when the assistant
                        inspects that method; the model note also flags that
                        "this method has a note". For the rules of one single
                        operation.
======================  ==========================================================

5.3 Writing a note
------------------

Notes live in the **Settings > Technical > MCP Notes** menu (developer mode
must be active for the Technical menu). Only users with the **MCP Admin** role
can write and edit them.

1. Click **New**.
2. **Title**: the short name of the note. It is shown to the assistant as
   ``- Title: content``, so the title carries information too; choose a
   meaningful one.
3. **Model**: pick the model concerned, or leave empty for a global note.
4. **Method**: appears once a model is chosen. To target a single method enter
   its technical name (e.g. ``action_confirm``, ``unlink``).
5. **Sequence**: display order of the notes in the same scope; the lower
   number comes first.
6. **Content**: what the assistant should know.
7. Save. The note takes effect at the assistant's next connection or model
   inspection; no server restart is needed.

The module ships with a global note called **ORM vocabulary** (create = insert,
write = update, unlink = delete…). You need not touch it; edit it if you wish.

5.4 Examples
------------

**Global note — company glossary**

  :Title: Company glossary
  :Model: *(empty)*
  :Content: "Bayi" means a partner tagged with the category "Dealer"
            (res.partner.category). "Merkez" is the company
            "Eurotray Merkez" (company id 1). Amounts are in TRY unless the
            record says otherwise; prices exclude VAT.

**Global note — behaviour rule**

  :Title: Ask before changing data
  :Model: *(empty)*
  :Content: Before creating, updating or deleting any record, summarise what
            will change and wait for the user's explicit confirmation. Never
            delete records: archive them instead (write active = false).

**Model note — sales order**

  :Title: Order states
  :Model: Sales Order (``sale.order``)
  :Content: state 'draft' and 'sent' are quotations, 'sale' is a confirmed
            order, 'cancel' is cancelled. "Open orders" means state = 'sale'
            with invoice_status != 'invoiced'. The custom field
            x_project_code holds the customer's project reference and is
            mandatory for dealers.

**Model note — customer**

  :Title: Customer vs vendor
  :Model: Contact (``res.partner``)
  :Content: Customers have customer_rank > 0, vendors have supplier_rank > 0.
            Use company_type = 'company' for companies; individual contacts of
            a company have parent_id set. Phone numbers are stored in 'phone';
            there is no separate mobile field.

**Method note — order confirmation**

  :Title: Confirmation rule
  :Model: Sales Order (``sale.order``)
  :Method: ``action_confirm``
  :Content: Only confirm an order when the user asks for it explicitly and the
            order has at least one line. Confirmation creates a delivery and
            cannot be undone from the assistant; tell the user this first.

**Method note — deletion ban**

  :Title: Do not delete invoices
  :Model: Journal Entry (``account.move``)
  :Method: ``unlink``
  :Content: Posted invoices must never be deleted; legal numbering would break.
            Use button_draft + button_cancel to cancel, or create a credit note
            with action_reverse.

5.5 Tips for good notes
-----------------------

- **Be short and precise.** Every note's content takes up room in the
  assistant's memory; needlessly long notes cost money and distract.
- **Write in the assistant's language.** The assistant reads whichever
  language the note is written in; leave technical names (``sale.order``,
  ``action_confirm``) as they are.
- **Pick the right scope.** Do not make a global note out of something not
  needed in every conversation; attach it to the model or method concerned.
  Global notes are sent with every connection.
- **State prohibitions explicitly.** "Do not do this" sentences are the
  instructions the assistant follows best. They are still requests, not real
  barriers; use Odoo access rights for hard prohibitions (section 6).
- **Watch the users.** When the assistant misunderstands a question or uses
  the wrong field, write a note that corrects that mistake. Notes mature over
  time this way.

----

6. Security Notes
=================

- **Every call runs as the user who owns the key.** Access rights and record
  rules apply as in the Odoo interface. The more privileged the account given
  to the assistant, the more it can do; prefer the least privileged suitable
  account.
- **The MCP User role is mandatory.** A user without it is refused even with
  a valid key. To cut a user's assistant access, clearing the role is enough;
  deleting the key is not required.
- **Give keys an expiry.** An expired key switches itself off. When an
  employee leaves or a device is lost, delete the key from the profile screen.
- **Use HTTPS.** The key travels as a header with every request.
- **MCP notes are not a barrier.** The assistant may ignore a note; build real
  restrictions with Odoo access rights.
- **Every tool call** is written to the Odoo server log with the user, the
  tool and the parameters used.

----

7. Troubleshooting
==================

=====================================================  ==============================================
Symptom                                                Fix
=====================================================  ==============================================
``401 Invalid apikey``                                 The key is wrong, deleted or expired.
                                                       Generate a new one. Make sure the header
                                                       has the form ``Bearer`` + space + key.
``401 User not authenticated``                         The request carries no Authorization
                                                       header at all. Check the header in the
                                                       client settings.
``403 User is not a member of the MCP User group``     The user has no MCP role (section 2.3).
``403 Origin not allowed``                             The request comes from a browser and its
                                                       site is not allowed. Add the address to
                                                       the **MCP Allowed Origins** setting
                                                       (section 3.6).
``400 Unsupported protocol version``                   The client asks for an MCP version BigMCP
                                                       does not know. The ``supported`` list in
                                                       the answer shows the supported ones;
                                                       update the client.
``400 Header mismatch``                                The client sends the mandatory headers of
                                                       the modern revision missing or wrong; a
                                                       client-side problem.
``404 Method not found``                               A modern client asked for a feature BigMCP
                                                       does not offer (e.g. resources,
                                                       subscriptions). Only tools are supported.
Assistant says "Truncated… ask for fewer fields"       The result exceeded the size limit. Wait
                                                       for the assistant to narrow the request or
                                                       raise the **MCP Result Limit** setting.
Assistant cannot find a model                          The user has no read access to that model,
                                                       or the assistant searches with the wrong
                                                       term. Give the technical name (e.g.
                                                       invoices are ``account.move``) or define
                                                       the term in a global note.
Assistant does not know company rules                  Write the knowledge as an MCP note
                                                       (section 5).
Claude Desktop does not show the server                Make sure the config file is valid JSON,
                                                       Node.js is installed and the app was fully
                                                       quit and reopened.
=====================================================  ==============================================
