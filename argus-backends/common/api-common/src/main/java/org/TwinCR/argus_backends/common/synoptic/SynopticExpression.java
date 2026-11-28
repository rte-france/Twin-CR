/*
Copyright (c) 2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

package org.TwinCR.argus_backends.common.synoptic;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Small arithmetic expression language used by the synoptic diagrams.
 *
 * <pre>
 *   expr     := or
 *   or       := and ('||' and)*
 *   and      := cmp ('&&' cmp)*
 *   cmp      := add (('<'|'<='|'>'|'>='|'=='|'!=') add)?
 *   add      := mul (('+'|'-') mul)*
 *   mul      := unary (('*'|'/'|'%') unary)*
 *   unary    := ('-'|'!') unary | primary
 *   primary  := number | string | name '(' args? ')' | '(' expr ')'
 * </pre>
 * Strings ('...' or "...") are only allowed as function arguments (equipment / telemetry ids).
 * Every value is a double; NaN means "unknown" and is propagated (displayed as "?").
 */
public final class SynopticExpression {

    /** Resolves the function calls of an expression. */
    public interface Functions {
        double call(String name, List<Object> args);
    }

    sealed interface Node permits Num, Str, Unary, Binary, Call {}
    record Num(double value) implements Node {}
    record Str(String value) implements Node {}
    record Unary(char op, Node arg) implements Node {}
    record Binary(String op, Node left, Node right) implements Node {}
    record Call(String name, List<Node> args) implements Node {}

    private final String source;
    private final Node root;

    private SynopticExpression(String source, Node root) {
        this.source = source;
        this.root = root;
    }

    public String source() {
        return source;
    }

    public static SynopticExpression parse(String source) {
        Parser p = new Parser(source);
        Node node = p.expr();
        p.skipSpaces();
        if (p.pos != source.length()) {
            throw p.error("unexpected '" + source.charAt(p.pos) + "'");
        }
        return new SynopticExpression(source, node);
    }

    public double evaluate(Functions functions) {
        return eval(root, functions);
    }

    /** Collect the string arguments (equipment / telemetry ids) used in the expression. */
    public void collectIds(Set<String> ids) {
        collect(root, ids);
    }

    /** Collect the string arguments of the calls to function {@code name} (e.g. the countries of exchange('FR', 'BE')). */
    public void collectCalls(String name, List<List<String>> calls) {
        collectCalls(root, name, calls);
    }

    private static void collectCalls(Node node, String name, List<List<String>> calls) {
        switch (node) {
            case Unary u -> collectCalls(u.arg(), name, calls);
            case Binary b -> {
                collectCalls(b.left(), name, calls);
                collectCalls(b.right(), name, calls);
            }
            case Call c -> {
                if (c.name().equals(name)) {
                    List<String> args = new ArrayList<>();
                    for (Node a : c.args()) {
                        args.add(a instanceof Str s ? s.value() : null);
                    }
                    calls.add(args);
                }
                c.args().forEach(a -> collectCalls(a, name, calls));
            }
            case Num n -> { }
            case Str s -> { }
        }
    }

    private static void collect(Node node, Set<String> ids) {
        switch (node) {
            case Str s -> ids.add(s.value());
            case Unary u -> collect(u.arg(), ids);
            case Binary b -> {
                collect(b.left(), ids);
                collect(b.right(), ids);
            }
            case Call c -> c.args().forEach(a -> collect(a, ids));
            case Num n -> { }
        }
    }

    private static boolean truthy(double v) {
        return !Double.isNaN(v) && v != 0;
    }

    private static double eval(Node node, Functions f) {
        return switch (node) {
            case Num n -> n.value();
            case Str s -> throw new IllegalArgumentException("string '" + s.value() + "' used as a number");
            case Unary u -> {
                double v = eval(u.arg(), f);
                if (u.op() == '-') {
                    yield -v;
                }
                yield Double.isNaN(v) ? Double.NaN : (v == 0 ? 1 : 0);
            }
            case Binary b -> evalBinary(b, f);
            case Call c -> evalCall(c, f);
        };
    }

    private static double evalBinary(Binary b, Functions f) {
        // Short-circuit logical operators
        if (b.op().equals("&&")) {
            double l = eval(b.left(), f);
            if (!Double.isNaN(l) && l == 0) {
                return 0;
            }
            double r = eval(b.right(), f);
            if (Double.isNaN(l) || Double.isNaN(r)) {
                return Double.NaN;
            }
            return r != 0 ? 1 : 0;
        }
        if (b.op().equals("||")) {
            double l = eval(b.left(), f);
            if (truthy(l)) {
                return 1;
            }
            double r = eval(b.right(), f);
            if (truthy(r)) {
                return 1;
            }
            return Double.isNaN(l) || Double.isNaN(r) ? Double.NaN : 0;
        }
        double l = eval(b.left(), f);
        double r = eval(b.right(), f);
        if (Double.isNaN(l) || Double.isNaN(r)) {
            return Double.NaN;
        }
        return switch (b.op()) {
            case "+" -> l + r;
            case "-" -> l - r;
            case "*" -> l * r;
            case "/" -> r == 0 ? Double.NaN : l / r;
            case "%" -> r == 0 ? Double.NaN : l % r;
            case "<" -> l < r ? 1 : 0;
            case "<=" -> l <= r ? 1 : 0;
            case ">" -> l > r ? 1 : 0;
            case ">=" -> l >= r ? 1 : 0;
            case "==" -> l == r ? 1 : 0;
            case "!=" -> l != r ? 1 : 0;
            default -> throw new IllegalStateException("unknown operator " + b.op());
        };
    }

    private static double evalCall(Call c, Functions f) {
        List<Node> argNodes = c.args();
        switch (c.name()) {
            case "if" -> {
                if (argNodes.size() != 3) {
                    throw new IllegalArgumentException("if(cond, then, else) expects 3 arguments");
                }
                double cond = eval(argNodes.get(0), f);
                if (Double.isNaN(cond)) {
                    return Double.NaN;
                }
                return eval(argNodes.get(cond != 0 ? 1 : 2), f);
            }
            case "coalesce" -> {
                // First known (non NaN) argument
                for (Node a : argNodes) {
                    double v = eval(a, f);
                    if (!Double.isNaN(v)) {
                        return v;
                    }
                }
                return Double.NaN;
            }
            case "isnan" -> {
                return Double.isNaN(eval(argNodes.get(0), f)) ? 1 : 0;
            }
            default -> { }
        }

        List<Object> args = new ArrayList<>(argNodes.size());
        boolean numeric = true;
        for (Node a : argNodes) {
            if (a instanceof Str s) {
                args.add(s.value());
                numeric = false;
            } else {
                args.add(eval(a, f));
            }
        }
        if (numeric) {
            Double math = math(c.name(), args);
            if (math != null) {
                return math;
            }
        }
        return f.call(c.name(), args);
    }

    // Built-in math functions, null if the name is not one of them
    private static Double math(String name, List<Object> args) {
        double[] v = args.stream().mapToDouble(o -> (Double) o).toArray();
        switch (name) {
            case "abs": return Math.abs(v[0]);
            case "round": return v.length > 1 ? Math.round(v[0] / v[1]) * v[1] : (double) Math.round(v[0]);
            case "floor": return Math.floor(v[0]);
            case "ceil": return Math.ceil(v[0]);
            case "sqrt": return Math.sqrt(v[0]);
            case "sign": return Math.signum(v[0]);
            case "nan": return Double.NaN;
            case "min":
            case "max":
            case "sum": {
                double acc = name.equals("sum") ? 0 : Double.NaN;
                for (double x : v) {
                    if (Double.isNaN(x)) {
                        return Double.NaN;
                    }
                    acc = switch (name) {
                        case "sum" -> acc + x;
                        case "min" -> Double.isNaN(acc) ? x : Math.min(acc, x);
                        default -> Double.isNaN(acc) ? x : Math.max(acc, x);
                    };
                }
                return acc;
            }
            default: return null;
        }
    }

    private static final class Parser {
        private final String s;
        private int pos = 0;

        Parser(String s) {
            this.s = s;
        }

        IllegalArgumentException error(String msg) {
            return new IllegalArgumentException("Expression '" + s + "' at " + pos + ": " + msg);
        }

        void skipSpaces() {
            while (pos < s.length() && Character.isWhitespace(s.charAt(pos))) {
                pos++;
            }
        }

        boolean eat(String token) {
            skipSpaces();
            if (s.startsWith(token, pos)) {
                pos += token.length();
                return true;
            }
            return false;
        }

        Node expr() {
            Node left = and();
            while (eat("||")) {
                left = new Binary("||", left, and());
            }
            return left;
        }

        Node and() {
            Node left = cmp();
            while (eat("&&")) {
                left = new Binary("&&", left, cmp());
            }
            return left;
        }

        Node cmp() {
            Node left = add();
            for (String op : new String[] {"<=", ">=", "==", "!=", "<", ">"}) {
                if (eat(op)) {
                    return new Binary(op, left, add());
                }
            }
            return left;
        }

        Node add() {
            Node left = mul();
            while (true) {
                if (eat("+")) {
                    left = new Binary("+", left, mul());
                } else if (eat("-")) {
                    left = new Binary("-", left, mul());
                } else {
                    return left;
                }
            }
        }

        Node mul() {
            Node left = unary();
            while (true) {
                if (eat("*")) {
                    left = new Binary("*", left, unary());
                } else if (eat("/")) {
                    left = new Binary("/", left, unary());
                } else if (eat("%")) {
                    left = new Binary("%", left, unary());
                } else {
                    return left;
                }
            }
        }

        Node unary() {
            if (eat("-")) {
                return new Unary('-', unary());
            }
            skipSpaces();
            if (pos < s.length() && s.charAt(pos) == '!' && !s.startsWith("!=", pos)) {
                pos++;
                return new Unary('!', unary());
            }
            return primary();
        }

        Node primary() {
            skipSpaces();
            if (pos >= s.length()) {
                throw error("unexpected end");
            }
            char c = s.charAt(pos);
            if (c == '(') {
                pos++;
                Node n = expr();
                if (!eat(")")) {
                    throw error("missing ')'");
                }
                return n;
            }
            if (c == '\'' || c == '"') {
                int end = s.indexOf(c, pos + 1);
                if (end < 0) {
                    throw error("unterminated string");
                }
                String str = s.substring(pos + 1, end);
                pos = end + 1;
                return new Str(str);
            }
            if (Character.isDigit(c) || c == '.') {
                int start = pos;
                while (pos < s.length() && (Character.isDigit(s.charAt(pos)) || s.charAt(pos) == '.'
                    || s.charAt(pos) == 'e' || s.charAt(pos) == 'E'
                    || ((s.charAt(pos) == '-' || s.charAt(pos) == '+') && (s.charAt(pos - 1) == 'e' || s.charAt(pos - 1) == 'E')))) {
                    pos++;
                }
                return new Num(Double.parseDouble(s.substring(start, pos)));
            }
            if (Character.isLetter(c) || c == '_') {
                int start = pos;
                while (pos < s.length() && (Character.isLetterOrDigit(s.charAt(pos)) || s.charAt(pos) == '_')) {
                    pos++;
                }
                String name = s.substring(start, pos);
                if (!eat("(")) {
                    throw error("expected '(' after function name " + name);
                }
                List<Node> args = new ArrayList<>();
                if (!eat(")")) {
                    do {
                        args.add(expr());
                    } while (eat(","));
                    if (!eat(")")) {
                        throw error("missing ')' after arguments of " + name);
                    }
                }
                return new Call(name, args);
            }
            throw error("unexpected '" + c + "'");
        }
    }
}
