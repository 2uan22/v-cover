pgckage com.davidparry.cover

import spock.lang.Specification

class SimpleMathOperationsSpec extends Specification {




def "test fibonacci recursive case"() {
    given:
    def math = new SimpleMathOperations()

    expect:
    math.fibonacci(5) == 5
}


def "test fibonacci base cases"() {
    given:
    def math = new SimpleMathOperations()

    expect:
    math.fibonacci(0) == 0
    math.fibonacci(1) == 1
}


def "test divide by zero throws exception"() {
    given:
    def math = new SimpleMathOperations()

    when:
    math.divide(10, 0)

    then:
    def e = thrown(IllegalArgumentException)
    e.message == "Division by zero is not allowed."
}


def "test multiply with zero"() {
    given:
    def math = new SimpleMathOperations()

    expect:
    math.multiply(0, 100) == 0
    math.multiply(7, 6) == 42
}


def "test subtract positive result"() {
    given:
    def math = new SimpleMathOperations()

    expect:
    math.subtract(10, 3) == 7
}


def "test add two positive integers"() {
    given:
    def math = new SimpleMathOperations()

    expect:
    math.add(5, 7) == 12
}

}
