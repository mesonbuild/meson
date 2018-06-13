project('javamaven', 'java')

junit_dep = dependency('junit', fallback : ['junit', 'junit_dep'])
hamcrest_dep = dependency('hamcrest', fallback : ['hamcrest', 'hamcrest_dep'])

test = jar('TestClass', 'TestClass.java',
           dependencies: [junit_dep, hamcrest_dep])