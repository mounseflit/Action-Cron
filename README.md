### Keep your server alive for free

Traditionally if you use renders free plan, they shut down your server after 15 minutes of inactivity. With this repo, you can keep your server alive constantly by pinging it ever 5 minutes!



Steps:
1. Clone the repo
2. In main.py change the url to your respective server url & endpoint such as https://hello-world.org/ping
3. create your own github repo and navigate to the actions tab, which is located between your pull requests and projects.
4. On the actions tab, you should see something called 'Keep Backend Alive', click on it and click Run Workflow
5. You're all set!

   Note that github actions isn't always 100% accurate, there are times where instead of pinging every 5 minutes like we want it to, it may ping it with a delay (5-10 minutes) when servers are busy.
   
