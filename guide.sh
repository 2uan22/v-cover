cd /templated_tests/java_spring_calculator
export OPENROUTER_API_KEY="<OPENROUTER_API_KEY>"
--project-language="java"
--project-root="/Users/mac/Documents/Opensource/qodo-cover/templated_tests/java_spring_calculator"
--coverage-type="jacoco"
--desired-coverage=80
--code-coverage-report-path="target/site/jacoco/jacoco.csv"
--test-command="mvn verify -DfailIfNoTests=false"
--test-command-dir="/Users/mac/Documents/Opensource/qodo-cover/templated_tests/java_spring_calculator"
--model="openrouter/anthropic/claude-sonnet-4"