import { providerConfig, providerDescriptors } from "@/api/mocks/fixtures/providers";
import type { ProviderChoice } from "@/api/types";
import {
  activeProvider,
  addableProviders,
  capabilitiesOf,
  capabilityTitle,
  chainFor,
  hasOptions,
  moveChoice,
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
  it.each([
    ["llm", "Text generation"],
    ["tts", "Narration"],
    ["sound_fx", "Sound fx"],
  ])("titles the %s capability", (capability, title) => {
    expect(capabilityTitle(capability)).toBe(title);
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
