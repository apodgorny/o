# WordWield: Agent Execution Context

## Core idea

In WordWield there should be a context object that has `tree`.
Agents are called as:

`ww.agents.Foobar()`

They should return a context object that has all available agents hooked as properties.
So each tree can be called an agent upon itself.
And they can be chained.

## Context

A `Context` has `tree`.
Every agent call returns `Context`.
The returned `Context` has all available agents as properties.

This makes chaining natural.

## Tree as context

`o.tree` can be the context.
That way all available agent operations can be done automatically on the tree.

## Agent calls

An agent is not a function that returns text and ends.
An agent call returns more context.

So the pattern is:
- current tree
- apply agent
- get updated context
- continue through other agents

## Chaining

Because each agent returns `Context`, calls can be chained.

## augment and extend

- `augment()` means develop this same tree in place
- `extend()` means create a subtype

`augment()` can add properties that are agents.
So trees can gain callable agent-properties without becoming a new subtype.

