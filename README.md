# Log4j CVE-2021-44228 checker

Checks a list of URLs with `POST` and `GET` requests in combination with parameters.

Heavily inspired by [NortwaveSecurity version](https://github.com/NorthwaveSecurity/log4jcheck).

# Set-up
## URLs to check
The list of URLs to check should be in the following format (`csv`):
```csv
description,URL,method,parameters
production,example.com/login,POST,"username,password"
staging,example.com/search,GET,"q"
development,example.com/,GETNP,""
```

This will subsequently run a `POST` request on `example.com/login` where the following raw body is posted: 
```username={jndi:ldap...}&password={jndi:ldap...}```

Similarly, it will run the following `GET` request: `example.com/search?q={jndi:ldap...}`.

Alternatively you can specify `GETNP` (`GET` `N`o `P`arameters) to do the `GET` the url with the payload appended: `example.com/new/{jndi:ldap...}`.

Additionally the payload is also inserted in the `User-Agent`, `Referer`, `X-Forwarded-For`, `Authentication` headers to increase the chances for a hit.

If you want to check URLs for both `GET`, `POST` or `GETNP`, please duplicate the entry in the CSV.

## Canary Token
To set-up without any prior configurations you can use [https://canarytokens.org/generate](https://canarytokens.org/generate) and create a Log4Shell CanaryToken:

![Canary Tokens](images/2021-12-12-19-01-55.png)

Alternatively, you can [set-up your own DNS server](https://github.com/NorthwaveSecurity/log4jcheck).

# Running the script
Install dependencies by using `pip install-r requirements.txt`. Edit the script to change the following line to your preferred canary token:

Now the script can be run, pointing the script to the prior created CSV with URLs to check.
```
python3 .\log4jcheck.py --file .\urls-example.csv --threads 2 --url "L4J.ujz5sgvgo7xuvn03ft9qrws5w.canarytokens.com/a" -w 0 -t 1
```

Check if the token has been triggered after the script has been completed. You will be able to cross correlate which application triggered based on the generated `UUID4` in combination with the injected parameter, e.g.: `40852c3b-2d6b-4bd5-a91f-4416aa730619-username`.


## Testing
Tested against [log4shell-vulnerable-app](https://github.com/christophetd/log4shell-vulnerable-app). Modify the `MainControll.java` as follows:

```
package fr.christophetd.log4shell.vulnerableapp;


import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

@RestController
public class MainController {

    private static final Logger logger = LogManager.getLogger("HelloWorld");

    @GetMapping("/")
    public String index(@RequestHeader("X-Api-Version") String apiVersion) {
        logger.info("Received a request for API version " + apiVersion);
        return "Hello, world!";
    }

    @GetMapping("/test")
    public String testGet(@RequestParam String test) {
        logger.info("Received a request for test " + test);
        return "Test world!";
    }

    @PostMapping("/test")
    public String test(@RequestBody String test) {
        logger.info("Received a request for test " + test);
        return "Test world!";
    }

}
```

Compile and run:

```
gradle bootJar --no-daemon
java -jar .\build\libs\log4shell-vulnerable-app-0.0.1-SNAPSHOT.jar
```

Run the `log4jcheck` with the following `urls.csv` file:
```
description,URL,method,parameters
test,http://localhost:8080/test,POST,"test"
test,http://localhost:8080/test,GET,"test"
```

The following information should appear in the canary token log:
![Log input](images/2021-12-12-19-38-56.png)


## Coverage:

The following HTTP headers are covered:

* `X-Api-Version`
* `User-Agent`
* `Referer`
* `X-Druid-Comment`
* `Origin`
* `Location`
* `X-Forwarded-For`
* `Cookie`
* `X-Requested-With`
* `X-Forwarded-Host`
* `Accept`

For each injection, the following JNDI prefixes are possible:

* 0: `jndi:dns`
* 1: `jndi:${lower:l}${lower:d}ap`
* 2: `jndi:rmi`
* 3: `jndi:ldap`


## DISCLAIMER
Note that the script only performs checks the: *User Agent* and any parameters you specify to either the `POST` or `GET` request. This will cause false negatives in cases where other headers, missed input fields, etcetera need to be targeted to trigger the vulnerability. Feel free to add extra checks to the script.

## License

Log4jcheck is open-sourced software licensed under the MIT license.
