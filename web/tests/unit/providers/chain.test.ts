import { providerConfig, providerDescriptors } from "@/api/mocks/fixtures/providers";
import type { ProviderChoice } from "@/api/types";
import {
  activeProvider,
  addableProviders,
  capabilitiesOf,
  cardError,
  chainChanged,
  chainDescription,
  chainFor,
  choiceErrors,
  configErrors,
  defaultOrderDescription,
  hasOptions,
  moveChoice,
  newChoice,
  patchChoice,
  removeChoice,
  withChain,
} from "@/features/providers/chain";
import { itemAt } from "../../helpers/itemAt";

const choice = (provider_id: string, enabled = true): ProviderChoice => ({
  provider_id,
  enabled,
  options: {},
});
const chain = [choice("a"), choice("b"), choice("c")];
const ids = (items: ProviderChoice[]) => items.map((c) => c.provider_id);

describe("provider chains", () => {
  it("describes the active provider or the lack of one", () => {
    expect(chainDescription(itemAt(providerDescriptors, 0))).toBe(
      "Runs use Ollama, then fall back down the list.",
    );
    expect(chainDescription(undefined)).toBe(
      "No available provider is enabled. Runs that need this will fail.",
    );
  });

  it("creates enabled choices and detects unsaved chain changes", () => {
    expect(newChoice("x")).toEqual({ provider_id: "x", enabled: true, options: {} });
    expect(chainChanged(providerConfig, structuredClone(providerConfig))).toBe(false);
    expect(chainChanged(withChain(providerConfig, "llm", []), providerConfig)).toBe(true);
  });

  it("includes the media capability from the catalog", () => {
    expect(capabilitiesOf({ config: providerConfig, descriptors: providerDescriptors })).toContain(
      "media",
    );
  });

  it("orders capabilities by config, then descriptors, without duplicates", () => {
    const descriptor = itemAt(providerDescriptors, 0);
    const response = {
      config: [{ capability: "tts", chain: [] }],
      descriptors: [
        descriptor,
        { ...descriptor, capability: "tts" },
        { ...descriptor, capability: "x" },
      ],
    };
    expect(capabilitiesOf(response)).toEqual(["tts", "llm", "x"]);
  });

  it("reads and replaces chains, adding a missing capability", () => {
    expect(chainFor(providerConfig, "nothing")).toEqual([]);
    const llm = chainFor(providerConfig, "llm");
    expect(llm.length).toBeGreaterThan(0);
    const replaced = withChain(providerConfig, "llm", []);
    expect(chainFor(replaced, "llm")).toEqual([]);
    expect(replaced).toHaveLength(providerConfig.length);
    expect(withChain(providerConfig, "new", chain)).toHaveLength(providerConfig.length + 1);
  });

  it.each([
    [0, 1, ["b", "a", "c"]],
    [2, -1, ["a", "c", "b"]],
    [0, -1, ["a", "b", "c"]],
    [2, 1, ["a", "b", "c"]],
  ] as const)("moves item %d by %d", (index, delta, expected) => {
    expect(ids(moveChoice(chain, index, delta))).toEqual(expected);
  });

  it("patches and removes a choice by position", () => {
    expect(patchChoice(chain, 1, { enabled: false })[1]?.enabled).toBe(false);
    expect(ids(removeChoice(chain, 0))).toEqual(["b", "c"]);
  });

  it("offers only unused providers of the capability", () => {
    const llm = providerDescriptors.filter((d) => d.capability === "llm");
    const first = itemAt(llm, 0);
    const addable = addableProviders(providerDescriptors, "llm", [choice(first.provider_id)]);
    expect(addable.map((d) => d.provider_id)).toEqual(llm.slice(1).map((d) => d.provider_id));
  });

  it("picks the first enabled and available provider", () => {
    const descriptors = [itemAt(providerDescriptors, 0), itemAt(providerDescriptors, 1)];
    expect(activeProvider([choice("gemini"), choice("ollama")], descriptors)?.provider_id).toBe(
      "ollama",
    );
    expect(activeProvider([choice("ollama", false)], descriptors)).toBeUndefined();
  });

  it("detects option forms", () => {
    expect(hasOptions(providerDescriptors[0])).toBe(true);
    expect(
      hasOptions({ ...itemAt(providerDescriptors, 0), options_schema: { type: "object" } }),
    ).toBe(false);
    expect(hasOptions(undefined)).toBe(false);
  });
});

describe("default provider order", () => {
  it("names every provider of the capability in registry order", () => {
    expect(defaultOrderDescription(providerDescriptors, "llm")).toBe(
      "No order saved: runs try Ollama, Google Gemini, Offline fake in turn.",
    );
  });

  it("says when no provider offers the capability", () => {
    expect(defaultOrderDescription(providerDescriptors, "video")).toBe(
      "No installed provider offers this capability.",
    );
  });
});

describe("provider save errors", () => {
  const fields = {
    "0.capability": "capability is configured twice",
    "0.chain.1.provider_id": "unknown provider 'nope'",
    "0.chain.1.options.topic_words": "Input should be a valid integer",
    "1.chain.0.options": "Input should be a valid dictionary",
  };

  it("scopes errors to the request index of the capability's config", () => {
    expect(configErrors(fields, providerConfig, "image")).toEqual({
      "chain.0.options": "Input should be a valid dictionary",
    });
    expect(configErrors(fields, providerConfig, "unsaved")).toEqual({});
  });

  it("drops errors for an index or key shape that matches no saved config", () => {
    expect(configErrors({ "5.capability": "x", body: "y" }, providerConfig, "llm")).toEqual({});
  });

  it("shows an unknown key of the card's own config on the card", () => {
    expect(cardError(configErrors({ "0.foo": "x" }, providerConfig, "llm"))).toBe("x");
  });

  it("finds the card error outside any chain entry", () => {
    const llm = configErrors(fields, providerConfig, "llm");
    expect(cardError(llm)).toBe("capability is configured twice");
    expect(cardError(configErrors(fields, providerConfig, "image"))).toBeUndefined();
  });

  it("splits one chain entry's errors into a message and option field errors", () => {
    const llm = configErrors(fields, providerConfig, "llm");
    expect(choiceErrors(llm, 1)).toEqual({
      message: "unknown provider 'nope'",
      options: { topic_words: "Input should be a valid integer" },
    });
    expect(choiceErrors(llm, 0)).toEqual({ message: undefined, options: {} });
    expect(choiceErrors(configErrors(fields, providerConfig, "image"), 0)).toEqual({
      message: "Input should be a valid dictionary",
      options: { "": "Input should be a valid dictionary" },
    });
  });
});
