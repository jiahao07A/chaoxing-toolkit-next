import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const script = fs.readFileSync(new URL("./学习通脚本.js", import.meta.url), "utf8");

const normalizeStart = script.indexOf("const normalizeJudgmentAnswer =");
const normalizeEnd = script.indexOf("  let defaultConfig = getConfig();", normalizeStart);
assert.ok(normalizeStart >= 0 && normalizeEnd > normalizeStart, "无法定位判断题答案归一化函数");
const normalizeJudgmentAnswer = new Function(
  `${script.slice(normalizeStart, normalizeEnd)}; return normalizeJudgmentAnswer;`
)();

const parseAnswerStart = script.indexOf("parseAIAnswer(content, questionTypeId, questionData) {");
const parseAnswerEnd = script.indexOf("    async getAnswerFromAI", parseAnswerStart);
assert.ok(parseAnswerStart >= 0 && parseAnswerEnd > parseAnswerStart, "无法定位 AI 答案解析函数");
const parseAIAnswer = new Function(
  "normalizeJudgmentAnswer",
  `return ({ ${script.slice(parseAnswerStart, parseAnswerEnd)} }).parseAIAnswer;`
)(normalizeJudgmentAnswer);

const setAnswerStart = script.indexOf("setAnswer = (answer, questionData, html, iframeWindow) =>");
const setAnswerEnd = script.indexOf(", matchAnswer =", setAnswerStart);
assert.ok(setAnswerStart >= 0 && setAnswerEnd > setAnswerStart, "无法定位答案填充函数");
const setAnswer = new Function(
  "normalizeJudgmentAnswer",
  "clearCurrent",
  "$$1",
  "matchAnswer",
  `return ${script.slice(setAnswerStart, setAnswerEnd).replace(/^setAnswer = /, "")}`
);

function createCollection(items, methods = {}) {
  return {
    length: items.length,
    each(callback) {
      items.forEach((item, index) => callback.call(item, index, item));
      return this;
    },
    is(selector) {
      if (selector === ":checked") return items.some((item) => item.checked);
      if (methods.is) return methods.is(selector, items);
      return false;
    },
    val() {
      return items[0]?.value;
    },
    attr(name) {
      return items[0]?.attributes?.[name];
    },
    click() {
      items.forEach((item) => {
        if (typeof item.click === "function") item.click();
      });
      return this;
    },
    find(selector) {
      if (methods.find) return methods.find(selector, items);
      return createCollection([]);
    },
    eq(index) {
      return createCollection(items[index] ? [items[index]] : [], methods);
    }
  };
}

function createQuestionDom(selectedValue = "") {
  const inputs = ["true", "false"].map((value) => ({
    value,
    checked: value === selectedValue,
    click() {
      inputs.forEach((input) => {
        input.checked = false;
      });
      this.checked = true;
    }
  }));
  const answerBgs = inputs.map((input) => ({
    input,
    attributes: { data: input.value },
    active: input.checked,
    click() {
      this.active = true;
    }
  }));
  const root = { inputs, answerBgs };
  const dollar = (value) => {
    if (value === root) {
      return createCollection([root], {
        find(selector) {
          if (selector === "ul:eq(0) li :radio,:checkbox,textarea") return createCollection(inputs);
          if (selector === ".answerBg") return createCollection(answerBgs);
          return createCollection([]);
        }
      });
    }
    if (value?.input) {
      return createCollection([value], {
        find(selector, items) {
          if (selector === ".num_option") return createCollection(items.map((item) => ({ attributes: item.attributes })));
          if (selector === ".check_answer" || selector === ".check_answer_dx") {
            return createCollection(items.filter((item) => item.active));
          }
          return createCollection([]);
        }
      });
    }
    return createCollection([value]);
  };
  return { root, dollar };
}

function invokeSetAnswer(answer, selectedValue = "") {
  const { root, dollar } = createQuestionDom(selectedValue);
  let clearCalls = 0;
  const clearCurrent = () => {
    clearCalls += 1;
    root.inputs.forEach((input) => {
      input.checked = false;
    });
    root.answerBgs.forEach((answerBg) => {
      answerBg.active = false;
    });
  };
  const result = setAnswer(
    normalizeJudgmentAnswer,
    clearCurrent,
    dollar,
    () => []
  )(answer, { type: "3" }, root, {});
  return { result, clearCalls, inputs: root.inputs };
}

test("判断题归一化支持正向和负向表达", () => {
  const positive = ["正确", "对", "是", "√", "✔", "true", "TRUE", "yes", "y", "t", "1", "right", "T", "ri"];
  const negative = ["错误", "错", "否", "×", "✘", "false", "FALSE", "no", "n", "f", "0", "wrong", "F", "wr"];

  for (const value of positive) assert.equal(normalizeJudgmentAnswer(value), "正确", value);
  for (const value of negative) assert.equal(normalizeJudgmentAnswer(value), "错误", value);
});

test("AI 判断题解析使用同一套正负表达归一化", () => {
  const questionData = { options: [] };
  for (const value of ["正确", "是", "TRUE", "yes", "1", "ri"]) {
    assert.deepEqual(parseAIAnswer(value, "3", questionData), { valid: true, answer: ["正确"] });
  }
  for (const value of ["错误", "否", "FALSE", "no", "0", "wr"]) {
    assert.deepEqual(parseAIAnswer(value, "3", questionData), { valid: true, answer: ["错误"] });
  }
  assert.equal(parseAIAnswer("答案是错误还是正确", "3", questionData).valid, false);
});

test("判断题归一化支持包装文本并拒绝歧义答案", () => {
  assert.equal(normalizeJudgmentAnswer("答案：正确。"), "正确");
  assert.equal(normalizeJudgmentAnswer("标准答案 = FALSE"), "错误");
  assert.equal(normalizeJudgmentAnswer("（错误）"), "错误");
  assert.equal(normalizeJudgmentAnswer(["是"]), "正确");
  assert.equal(normalizeJudgmentAnswer(true), "正确");
  assert.equal(normalizeJudgmentAnswer(0), "错误");

  for (const value of ["", "未知", "不正确", "正确或错误", "答案是错误还是正确", null, undefined, ["正确", "错误"]]) {
    assert.equal(normalizeJudgmentAnswer(value), "", String(value));
  }
});

test("已有判断题暂存答案相同时不清空，答案不同时才替换", () => {
  const same = invokeSetAnswer("是", "true");
  assert.equal(same.result, "正确");
  assert.equal(same.clearCalls, 0);
  assert.equal(same.inputs[0].checked, true);
  assert.equal(same.inputs[1].checked, false);

  const changed = invokeSetAnswer("否", "true");
  assert.equal(changed.result, "错误");
  assert.equal(changed.clearCalls, 1);
  assert.equal(changed.inputs[0].checked, false);
  assert.equal(changed.inputs[1].checked, true);
});

function invokeModernAnswer({ type, answer, initial = [], markerOnly = false, updateState = true }) {
  let clearCalls = 0;
  let clicks = 0;
  const rows = ["true", "false"].map((value, index) => {
    const option = { attributes: { data: value, class: initial.includes(index) ? "num_option check_answer" : "num_option" } };
    return {
      option,
      attributes: { role: type === "1" ? "checkbox" : "radio", "aria-checked": markerOnly ? undefined : String(initial.includes(index)), class: "before-after" },
      click() {
        clicks++;
        if (!updateState) return;
        const wasSelected = this.option.attributes.class.includes("check_answer");
        if (type !== "1") rows.forEach((row) => {
          row.option.attributes.class = "num_option";
          if (!markerOnly) row.attributes["aria-checked"] = "false";
        });
        this.option.attributes.class = wasSelected ? "num_option" : "num_option check_answer";
        if (!markerOnly) this.attributes["aria-checked"] = String(!wasSelected);
      }
    };
  });
  const root = {};
  const wrap = (items) => createCollection(items, {
    is(selector, items) {
      return items.some((item) => selector.split(",").some((part) => item.attributes?.class?.split(" ").includes(part.trim().slice(1))));
    },
    find(selector, items) {
      if (items.includes(root)) return selector.includes('li[role="radio"]') ? wrap(rows) : wrap([]);
      if (selector === ".num_option") return wrap(items.flatMap((item) => item.option ? [item.option] : []));
      if (selector === ".check_answer, .check_answer_dx") return wrap(items.flatMap((item) => item.option?.attributes.class.includes("check_answer") ? [item.option] : []));
      return wrap([]);
    }
  });
  const result = setAnswer(normalizeJudgmentAnswer, () => { clearCalls++; }, (node) => wrap([node]), (answers, options) => answers.map((value) => options.indexOf(value)).filter((index) => index >= 0))(answer, { type, options: ["选项甲", "选项乙"] }, root, {});
  return { result, clearCalls, clicks, selected: rows.flatMap((row, index) => row.option.attributes.class.includes("check_answer") ? [index] : []) };
}

test("新式判断题选项按 data 映射并通过选项行选择", () => {
  const positive = invokeModernAnswer({ type: "3", answer: ["是"] });
  assert.equal(positive.result, "正确");
  assert.deepEqual(positive.selected, [0]);
  assert.equal(positive.clicks, 1);
  assert.equal(positive.clearCalls, 0);
  const negative = invokeModernAnswer({ type: "3", answer: ["否"], initial: [0] });
  assert.equal(negative.result, "错误");
  assert.deepEqual(negative.selected, [1]);
});

test("新式单选和判断题的相同暂存答案不触发切换或清空", () => {
  for (const [type, answer] of [["0", ["选项乙"]], ["3", ["错"]]]) {
    const result = invokeModernAnswer({ type, answer, initial: [1], markerOnly: true });
    assert.ok(result.result);
    assert.equal(result.clicks, 0);
    assert.equal(result.clearCalls, 0);
    assert.deepEqual(result.selected, [1]);
  }
});

test("新式多选只调整有差异的选项，不重复切换相同选项", () => {
  const result = invokeModernAnswer({ type: "1", answer: ["选项甲", "选项乙"], initial: [0] });
  assert.ok(result.result);
  assert.equal(result.clicks, 1);
  assert.equal(result.clearCalls, 0);
  assert.deepEqual(result.selected, [0, 1]);
});

test("新式选择题操作后没有实际选中状态时不得报告填答成功", () => {
  const result = invokeModernAnswer({ type: "0", answer: ["选项甲"], updateState: false });
  assert.equal(result.result, false);
  assert.deepEqual(result.selected, []);
});
