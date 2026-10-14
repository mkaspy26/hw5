# AI Prompts Log

## Setup: AI prompts log

**Prompt:**

> Create AI_prompts.md in hw5. here, you will add every prompt that i give you from now on. i will give you 1. the problem # 2. the title 3. a follow up prompt if i need, explaining what was missing in the first.

**Follow-up:** None

## Setup: Model for agents

**Prompt:**

> only use gpt-6-luna model for all the agents you're going to create

**Follow-up:** None

## Problem 2: Study the Campus Customs Database

**Prompt:**

> open data/campus_customs.db and look thru every table and its fields. Copy original file to data/campus_customs to data/campus_customs_new.db -- in later probelms we'll be updating the working copy. study the 3 open tickest so u c how they link to other tables. start output/harness.md. for each table, list the fields and one short line on y that table matters for the agents. this file will keep gettng added to in later probelms

**Follow-up:** None

## Problem 3: Build the MCP Server

**Prompt:**

> write an MCP serve in mcp_server/ using FastMCP. it will talik to data/campus_customs.new.db. you don't need to connect or run it right now. Every agent will use the tools in this MCP server. as we go we're gonna add to the tools but for now just write 3 tools u know you'll need for tickets in the databaae & name them clearly. never invent any data -- only reference the information in the database.
> in ourput/harness.md, list each of the 3 mcp tools and for every tool include which table it reads, which ticket it helpes unlock (101, 102, or 103) and 1 senetnce on y that tool is the right one for that ticekt. vague lines like "reads inventory" is too broad & not helpful enough -- i want you to tie the tool to the ticket.
> create a shrot mcp_server/README.md that explains what the MCP server is for, which database file it uses and the 3 tools it has
>
> separately, explain to me what FastMCP is.
> also /anthropic-skills:inside-out : which ticket  it helpes unlock (101, 102, or 103)

**Follow-up:** None

**Additional question:**

> but fastMCP makes an MCP server for anything? cuz the set of tools for each platform would look l=differently so its not like a copy paste set of code, it's a brain that builds MCPs & projects what shit you'll need for those tools and then builds it?

**Follow-up (what was missing):**

> i need more context (ex. where does which agent read this? when a user clicks smtgg or rquests smtg? : agent reads "tee, size S" → orders check_stock_and_price("CC-TEE-WHITE", "S") → FastMCP runs your function → the function reads inventory in campus_customs_new.db → qty: 0 goes back to the agent → the agent knows the tee is out of stock.
> also, idk what a tciket eveen is

**Additional question:**

> so does fastMCP basically create the surface of an MCP and which has a few basic functiosn and then it adds to that MCP as we go and as my separate agents try and execute tasks that require extracting info from, in this case, the db

**Additional question:**

> so what fastMCP does, in short, is it allows an AI, on request (as we go), to do wtvr it wants w the data in the db file,

**Additional question:**

> so fastmcp is not lik ethe rest mcps where ai asks smtg & the mcp searches its menu of code & picks which code the ai needs fo rthis task and then runs it & gives back the value to the ai, this one just creates the tools as per reading the AI's request and then approves it if its safe and runs teh code to access the db and answer the quetsion of the AI by handing it back the answer to its original question

**Additional question:**

> /anthropic-skills:inside-out fastmcp vs mcp servers

**Follow-up (what was missing):**

> make it clearer what an mcp does and for what. ex is it user wants smtg (order M t shirt -- give me other examples of actions) and then that request i sthe browser sending a req? (i thought a browser was smtg that produces a website) and then that req asks my agent? (hwo r they even connected and y my agent as opposed to a query in my database_ and then agent (it's an openai or claude agent?) asks the model (like a human query in a chatgpt chat?) luna about what to do and then the model tells the agent and the agent knows it has to extract smtg from the db so but it needs the mcp for connectivity and it has the tool to request to the mcp but the fastmcp is just a word doc and there's nothing actually in the mcp so the fastmcp writes the code neded for that req, runs it in the db that its connected to anfd then returns to the agent the answer of the req and then the agent gives it back to the browser which pops up on the wesbite?
> as u can tell, plz assume i have no context and explain things inside out

**Additional question:**

> include in ur explanatin what an MCP is -- it's a huge py file taht has the code for all the diff functions an agent can tell the mcp to run depending on what the agent's query is...right?

**Additional question:**

> so is this "MCP (Model Context Protocol) is the rulebook: how an agent and a server talk to each other. It's not a file. It's an agreement, like "every order must name a menu item and its inputs," published by Anthropic and used by OpenAI and others." is basically how an agent has to format its query to the MCP server? so how would that work? is it an agent that tries to query the server (in wtvr format) but then the MCP is like nah u gotta follow this format so the agent formats its query and then the MCP runs it?

**Additional question:**

> but the MCP is different depending on the platform so how's it possible that every agent knows how to speak to every MCP in their format (especially that we're creating new MCP servers)

**Additional question:**

> so the agent puts the query in MCP format but what actually is the MCP format -- is this like plain tex and is the agent putting out a name of a function where it scans all the "names" of functions on the MCP server and then the agent falls on the matching name and then knows it wants to run that fucntion under the name and then asks the MCP server to run it?

**Follow-up (what was missing):**

> the flow isnt clear to me. you're skipping too many steps. whenever you are referncing smtg u have to, in brackets, remind me of exactly what it iss. try again

**Follow-up (what was missing):**

> u have to be clearer: Agent program: a Python file we'll write in a later problem. It runs on your laptop and passes messages between everyone else.
> * Model: `gpt-6-luna`, the AI. It runs on OpenAI's computers, reads text and decides what to do. It can't touch your files.
> thats hwat u said. u must be more specific & clear like what "messages" between who's "everyone else" and what text does the model read and from who abd decides what type of things to do?
> be extremely precise and asume 0 literacy. try gaian

**Additional question:**

> so the agent is not the brain -- the model is. the agent is jus the messanger boeying code but the model is thinking about what tools r needed to solve the problem & gives thme 1 by 1 sequentially after agent comes back w the answer to run of tool 1

**Additional question:**

> an mcp server has to be "running" so how does it get to be running? any user's command? the agent that does it by itsefl?

**Additional question:**

> so an agent command to MCP server is essneitially a fucntion(s) request and the MCP server returns the answer after running it if the function is within the MCP server's toolbox>

**Additional question:**

> but tools/list and initialize is the beginning once and thats it or is it the beginning of each request to the mcp server

**Additional question:**

> it says databse opens "the MCP server's functions [inside server.py], to look up stock, invoices and rent." but actually it's the model that came up with this function (knew we needed it) and agent delivered to MCP to see if ppossible & MCP said yes it's possible & gives task to agent but it's actulaly the model's function, right?

**Additional question:**

> so claude came up with the fucntions, the agent now asks the model what to do an dthe model opens up claude's menu of fucntions in the tools.py and then picks the tool we want and then agent checks if that tool (a fucntion) is available on MCP server

**Additional question:**

> so claude picked the tools it can use it serve,py (wtf is tools.py then?) and then when there's a ticket, there's code that activates the agent.py (since agent has some sort of connection to the db) hat prompts the agen tt o grab the info from the ticket and then goes to MCP server (which connects to what?) to see the menu (basically to see what options r available) and he brings that to the luna model which then picks which tool and then agent brings this query in MCP format to the MCP server and then has it run the function & spit back the answwer which the agent brings to the browser in JSON.
> but i took the browser out of the equation here aside from the end

**Additional question:**

> so what prompst the first move in the chian of actions / how

**Additional question:**

> so the agent doesn tjsust open the database because it cant access it without the MCP, right?

**Additional question:**

> so say i run in terminal a command to activate the agent.py then it first checks (because of my instructions in md file) the db and then sees all the open tickets and takes them (all offline) and then goes to the db's MCP server to see what tools r available an dthen brings that menu to luna model & luna model picks which tool (aka functions of code) and then agent converts that request in MCP format & brings to MCP server who then runs that tool (code) and spits back answer in JSON to the agent who then takes that to pdate the db

**Additional question:**

> but doesnt the agent bring it to the model since there's no connection between MCP and model: 7. "The agent takes that to update the database." ❌ This is the big fix. The result goes back to the model [gpt-6-luna], not into the database. ...

**Additional question:**

> tell me specifically what happens to trigger this entire process (be very precise & clear) and also tell me specifically what happens when model spits back english answer to agent

**Additional question:**

> so is fastmcp basically someytihng that allows me to be able to make an mcp server for anything?

**Additional question:**

> but wdym cant i just get a model to make an MCP server ? i mean what's fastMCP even good for it doesnt look like i need it

## Problem 4: Add the MCP server to vibe coder and test each tool

**Prompt:**

> create .mcp.json in the project root (or however u save the local MCP server lists) which is the connection JSON text that basically adds my MCP server to this project so that you can call the tools (I actually am not sure i actually need this since i think this sounds like if i wanted another external vibe coder to connect or something -- let me know!)
> now, test each of the 3 mcp tools and save the evidence in output/mcp_smoke.json and for each tool include 1. the prompt i asked you 2. tool name 3. tool output (must match values in data/campus_customs_new.db)

**Follow-up:** None

## Problem 5: Build the Agent Team and Grow the MCP Tools

**Prompt:**

> Build the agentic team for campus customs using pydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Incldude prompts, models, and agent loops so that they can delegate work to each other iwth full connectivity. Put the agent prompts in backend/prompts/ -- one file per agent. PUt data types in backend/models.py, and the agent files under backend/. use the portkey_api_jey and only gpt-6-luna for every agent.  more detailed prompts that cover all aspects of an agent's work and scope are better than a generic prompt for the pormpts with the shop rules that agent needs.
> add any tools the agents need to the MCP server so they can work on tghe open tickets. shop gacts come from the mcp server over data/campus_customs_new.db -- don't invent a 2nd shop-tools layer that bypasses the MCP. Write the agents so they append to output/audit_trail.json. as they run: for each agent-loop step, record enough to audit later. keep appending to this file and don't wipe it after eahch run.
> in output/harness.md, list each agent and each MCP tool (including ones u add in this problem) along with which table the tool uses. add a short safety section that includes the guardrails a real business would want when agents touch real customers and real money and limits that keep tokens use in check.
> Update mcp_server/README.md so that the tool list is updated with what we currently have

**Follow-up:** None

## Problem 6: Plan the 3 Tickets

**Prompt:**

> Before u wrie the backend, write down what u expect the team to do on each open ticket. Build output/desk_tickets.html -- a page you can double click w one tab per ticket (101, 102, and 103) also, add empty cash and reflections tabs for later problems (keep placeholders there w "coming soon" for now). on each ticket tab, fill an "Expected" section only (leave room for an "Actual" section that we'll fill after we run the agents.
> for each ticket's expected section, write 1. who the boss should call first and why -- i think the first that the boss should call is the agent that would most likely be able to end the loop ASAP so for me that's the inventoyr agent since if we know there's no invenstory, directly it will end things. if inventoyr pases, then the facilities agent will be next because it will place the order in house which willl then trigger the customer service one to serve the customer's request of the order and tell him that his order is all good. then, on our back end, the accounting agent will run to update our sales. someo=times the customer service one will be triggered first when the cutsomer just opens a chatbot and asks for shit, which could end up in a triggering of the chain once again of invenory, facilities, customer service and accounting.  2. all the agent delegations u expect -- not "Boss calls everyone" -- i explianed in #1 who triggers who 3. whcih MCP tools u expect that run to use -- I expect the tool to run the most is the get invoice one since we will have tons of orders and then we will also have the check tsock and price one for customer requests in the chatbot but i dont expect the get lease and cash one to be triggered.
> We will compare what actually happens when the agents resolve the 3 tickets.

**Follow-up:** None

## Problem 7: Backend Routes

**Prompt:**

> The React frontend dashboard (which we will talk about soon) needs a backend it can call. In backend/main.py, use FastAPI and add routes that do the following:
>
> 1. return the 3 tickets and whether each is open or resolved
> 2. take a tickets id and run ur agent team on that ticket
> 3. return recent agent events -- what each agent said and which tools they used so the board can refresh
> 4. approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash)
> 5. approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actulaly changes cash)
> 6. return the current checking balance from cash_accounts
> 7. reset the database to the origianla valyes when u want to try a fresh run
>
> from the backend/ fodler, start the server with: uvicorn main:app --reload --port 8000
> This turns on ur backend at http://localhost:8000 so the frontend dashboard can call those routes.
> in output/harness.md, list each route in 1 line (what URL / what it does)

**Follow-up:** None

## Problem 8: Agent Dashboard

**Prompt:**

> build the frontedn dashboard in frontend/ with React + Vite + Typescript. the page should call the routes we just built with the last prompt and ta minimum the board should:
>
> 1. list all 3 ticketss
> 2. let you pick 1 ticket and start the agent team on it
> 3. show each agent and what they're saying/doing while the ticket runs
> 4. mark a ticket resolved when run finished
> 5. show a short summary of what each agent did on that ticket
> 6. let a human approve a py or purchase when asked
> 7. show the checking balance (it should dcrop after an approved pay)
>
> make the dashbooard look very nice & creative. i want it to be gothic / harry potter / these are the secrets / yale themed and as much as i like the fanyc font and playful language, when ur explaining, make sure ur very anal & precise & clear about what ur syaing so anyone w no conext can understand. i wnat each agent to have a code name like a member of a secret socitety while the boss is the founder of the secret society -- make it skull & bones.
> tell the front end to talk to the backend at http: //localhost:8000. on the backend, allow the vite page origin (usually http://localhost:5173) so the broswer is allowed to call those routes. start the baord with: npm run dev
> the opens the react desk in ur browser so u can pick tickets and watch agents.
> write output/design.md w what we chose for the dashbaord look (layout, how agents read differently, how resolved tickets and cash show up) and why -- including the creative choices that make it feel  special and something humans would actually enjoy using

**Follow-up:** None

## Problem 9: Resolve the Tickets

**Prompt:**

> B4 tetsing the agents on a full run over the 3 tickets, reste the working database data/campus_customs_new.db again so u start clean. note the starting checking balance. then run all 3 tcikest on the board (101, 102, 103) until each is resolved. open output/desk_tickets.html from Problem 6. on each ticket tab, fill the "Actual" Section from this run: which agents worked, what they delegated, and which tools they used. Keep ur "Expected" section so u can compare the 2.
> On the "Cash" tab of the same output/desk_tickets.html, itemize the money: 1. starting checking balance (after the reste) 2. for each ticket: how cash changed when that ticket resolved and why (which pay / purchase, dollar amount) 3. ending checking balance - it must match cash_accounts in the working database. the cash math MUST be double checked to be 100% accurate all the time.
> save output/resolved_tickets.json for each ticket: 1. id 2. final status 3. short outcome 4. what each agent contributed 5. any human approvals
> save output/resolved_board.html which is a page u can doubel click w a screesnhost of ur React board for each resolved tickte (101, 102, 103)
> append real runs to output/audit_trail.json. finish output/harness.md so it covers tables, mcp tools, the 5 agents, api routes, the dashboard, and safety rules.

**Follow-up:** None

## Problem 10: Reflection

**Prompt:**

> Open output/desk_tickets.html and fill the Reflection tab. Answer in my own vibe and be detailed and thorough: 1. How would I evaluate the performance of the agents on each ticket and y 2. For each ticket, how did Actual compare to the Expected plan I wrote earlier? 3. What would have been simpler as 1 agent w tools and y? 4. Describe 3 new problems campus customs might face that the agent team could solve given the tools we built 5. Describe 3 new problems Campus Customs might face that this agent team could not solve w the tools we built and explain the tools and agents I'd need to solve them? Tie every answer to this app and the 3 tickets you ran — use the ticket tabs & Cash tab on the same page as my evidence.
>
> here's my response, which you can separate or organize  into the breakdown of each question but i'm just gonna say all my reflections: ticket 1 I like how inventory was called first because the most pertinent issue is whether we have something in stock to ship. also, it unexepectdely but correctly triggered accoutning agent to immediately provide invoice to the customer which is the right step and then yes, the customer service agent to answer tauhid's reply. ticket 2 i realize that i thougth tickets would only be customer requests as opposed to requests from any of our steakholders so in this case where rent was requested, the boss correctly triggered the facilities agent. also, i like how accoutning agent is actually the one that manages all our finances & checks if we have the money to pay soemthing as opposed to just log or reconcile accounting transactions. i can see how havignn multiple agents. that can delegate to each other that the process was more precise & less costly (if it was 1 agent doing 100 steps as opposed to 10 agents doing 10 steps) then each agent has a smaller scope of responsility that they can nail instead of 1 agent having to be 100% accurate for all 100 steps and take longer to do that. my flow of actions were decently predicted but i didn't consider how tasks can be delegated in parallel, which speeds up the process. however, what one agent with tools could have simpplified is that the process didn't have to call the get ticket and delegate functions so many times isnce it would have the context of the ticket trhoughout the task and do all of the steps itself. i think that "less calling of the tools" saves power.  on tieckte 3, i like how the it spit back a ticket note for the club that wants 20 M hoodies when we only have 8 in stock and i love how it requested to human the bulk discount but what could make this better and (would solve problem of cutsomer not actually getting an answer for a while and having to wait for human to check the tickest) is to send a notification to the device of the owner when there's approval needed or human action needed. what could improve this also is have a tone & nice writing format to customers after it requests somethign so it feels like a convo, not like a robot outputting you things like when it said "Draft the club's reply: 8 ready now, rest needs a reprint, list price $58 ($1,160 for 20), bulk rate under review".  so a new problem that this team of agent could solve is weird new requests that the customer makes (ex. a bulk buying or maybe financing the payments, etc.) because the agent will make sure inventory is there, see if the business can afford not collecting cash for next week or two and afford that financed customer payment and then escalate the question to the human to then make the decision. a new problem I foresee is that with proposed discounts, there should be a structured minimum price we're willing to sell and structured process of when we're allowed to give refunds and i'd need a thinking tool that creates rules of what conditions can be allowd to give a refund and to administer it. with the tools we built, we can evaluate whether M&A is possible with our accounting agent that can tell us if we can finance the purchase in house and also we can, with the tools we can create solve problem of badly forecasting inventoyr management -- we can have agents reason to learn patterns of orders, inventory orders, etc. to have a forecasted inventory suggestions from AI that can be tailored seasonsally, colour, size, etc.a new problem is cash management if a bunch of payments r required at once (for rent, for prinitng new merch) and if they all come at same time but we have no money, we would need a new agent with tools that can suggest loans that scans the web and checks rates of banks to provide most optimal loan we need to finance our expenses and work with the inventory management agent that forecasts sales to see when our cash  would be coming so that the cash management agent can see if a loan is actually the best idea or if we should just ask supplier to extend our credit terms for a bit longer (the gaent would reason)

**Follow-up:** None

## Problem 11: Submit to GitHub

**Prompt:**

> [screenshot of the required hw5/ file tree: AI_prompts.md, requirements.txt, .env.example, .gitignore, .mcp.json, README.md, data/ (campus_customs.db, campus_customs_new.db), mcp_server/ (server.py, README.md), frontend/, backend/ (main.py, models.py, prompts/ boss.md, inventory.md, accounting.md, facilities.md, customer_service.md), output/ (harness.md, mcp_smoke.json, desk_tickets.html, design.md, resolved_tickets.json, resolved_board.html, audit_trail.json, github_url.txt)]
> Problem 11: Submit to GitHub.
> please make me a zip of hw5 that now in this exact file layout (this excludes some things and includes some new thing). be sure not to include the .env with my poytrkey api key in there. i will push this to github and then puyt that link in the github_url.txt
> READme shoudl explain: copy original DB to the working copy when u need a clean run, start MCP server, start FastAPI backend, start the React board, reset the DB b4 full 3 ticket run.

**Follow-up:** None
