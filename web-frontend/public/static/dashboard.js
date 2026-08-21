(() => {
  const palette = {
    accent: "#24b4f2",
    accentSoft: "rgba(36, 180, 242, 0.18)",
    fake: "#d94b58",
    fakeSoft: "rgba(217, 75, 88, 0.20)",
    real: "#119b7f",
    realSoft: "rgba(17, 155, 127, 0.18)",
    ink: "#13263f",
    inkSoft: "#5f7692",
    line: "rgba(58, 121, 197, 0.14)",
    bg: "rgba(255, 255, 255, 0.78)",
  };

  const modeNameMap = {
    image: "图片",
    video: "视频",
    audio: "音频",
  };

  function resolveModeLabel(fileType) {
    return modeNameMap[fileType] || fileType || "未知";
  }

  function formatPercent(value) {
    return `${(Number(value || 0) * 100).toFixed(1)}%`;
  }

  function truncateLabel(text, maxLength = 14) {
    if (!text || text.length <= maxLength) {
      return text || "";
    }
    return `${text.slice(0, maxLength - 1)}…`;
  }

  function buildChart(el, option) {
    if (!el || !window.echarts) {
      return null;
    }
    const chart = window.echarts.init(el);
    chart.setOption(option);
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return chart;
  }

  function baseGrid(extra = {}) {
    return {
      left: 12,
      right: 18,
      top: 36,
      bottom: 24,
      containLabel: true,
      ...extra,
    };
  }

  function axisStyle() {
    return {
      axisLine: {
        lineStyle: {
          color: palette.line,
        },
      },
      axisLabel: {
        color: palette.inkSoft,
      },
      splitLine: {
        lineStyle: {
          color: palette.line,
        },
      },
    };
  }

  function tooltipStyle(formatter) {
    return {
      trigger: "axis",
      backgroundColor: "rgba(19, 38, 63, 0.92)",
      borderWidth: 0,
      textStyle: {
        color: "#eef6ff",
      },
      formatter,
    };
  }

  function initBatchTrendChart(el, batches) {
    if (!el || !batches?.length) {
      return null;
    }
    return buildChart(el, {
      grid: baseGrid(),
      tooltip: tooltipStyle((params) => {
        const point = params[0];
        const batch = batches[point.dataIndex];
        return [
          `<strong>${batch.batch_name}</strong>`,
          `${resolveModeLabel(batch.file_type)} · ${batch.created_at || "未知时间"}`,
          `可疑率：${formatPercent(batch.suspicious_rate)}`,
          `平均分：${Number(batch.avg_score || 0).toFixed(3)}`,
          `样本数：${batch.item_count || 0}`,
        ].join("<br>");
      }),
      xAxis: {
        type: "category",
        data: batches.map((batch, index) => batch.short_label || `#${index + 1}`),
        ...axisStyle(),
      },
      yAxis: {
        type: "value",
        min: 0,
        max: 100,
        axisLabel: {
          color: palette.inkSoft,
          formatter: "{value}%",
        },
        splitLine: {
          lineStyle: {
            color: palette.line,
          },
        },
      },
      series: [
        {
          type: "line",
          smooth: true,
          data: batches.map((batch) => Number(((batch.suspicious_rate || 0) * 100).toFixed(1))),
          symbolSize: 8,
          itemStyle: {
            color: palette.accent,
          },
          lineStyle: {
            color: palette.accent,
            width: 3,
          },
          areaStyle: {
            color: palette.accentSoft,
          },
        },
      ],
    });
  }

  function initModeShareChart(el, modalities) {
    if (!el || !modalities?.length) {
      return null;
    }
    return buildChart(el, {
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(19, 38, 63, 0.92)",
        borderWidth: 0,
        textStyle: {
          color: "#eef6ff",
        },
        formatter: (params) => `${params.name}<br>样本数：${params.value} (${params.percent}%)`,
      },
      series: [
        {
          type: "pie",
          radius: ["52%", "76%"],
          center: ["50%", "54%"],
          avoidLabelOverlap: true,
          label: {
            color: palette.ink,
            formatter: "{b}\n{d}%",
          },
          labelLine: {
            lineStyle: {
              color: palette.line,
            },
          },
          itemStyle: {
            borderColor: "#ffffff",
            borderWidth: 2,
          },
          data: modalities.map((item) => ({
            name: resolveModeLabel(item.file_type),
            value: item.item_count,
            itemStyle: {
              color:
                item.file_type === "video"
                  ? palette.accent
                  : item.file_type === "audio"
                    ? "#7a9cff"
                    : "#54d9b9",
            },
          })),
        },
      ],
    });
  }

  function initModeRiskChart(el, modalities) {
    if (!el || !modalities?.length) {
      return null;
    }
    return buildChart(el, {
      grid: baseGrid({ top: 44 }),
      tooltip: tooltipStyle((params) => {
        const lines = [params[0].axisValue];
        params.forEach((param) => {
          lines.push(`${param.seriesName}：${param.value}`);
        });
        return lines.join("<br>");
      }),
      legend: {
        top: 8,
        textStyle: {
          color: palette.inkSoft,
        },
      },
      xAxis: {
        type: "category",
        data: modalities.map((item) => resolveModeLabel(item.file_type)),
        ...axisStyle(),
      },
      yAxis: {
        type: "value",
        ...axisStyle(),
      },
      series: [
        {
          name: "累计样本数",
          type: "bar",
          barMaxWidth: 28,
          itemStyle: {
            color: palette.accentSoft,
            borderColor: palette.accent,
            borderWidth: 1,
          },
          data: modalities.map((item) => item.item_count),
        },
        {
          name: "可疑样本数",
          type: "bar",
          barMaxWidth: 28,
          itemStyle: {
            color: palette.fake,
          },
          data: modalities.map((item) => item.fake_count),
        },
      ],
    });
  }

  function initModeLatencyChart(el, modalities) {
    if (!el || !modalities?.length) {
      return null;
    }
    return buildChart(el, {
      grid: baseGrid(),
      tooltip: tooltipStyle((params) => `${params[0].axisValue}<br>平均耗时：${Number(params[0].value || 0).toFixed(3)}s`),
      xAxis: {
        type: "category",
        data: modalities.map((item) => resolveModeLabel(item.file_type)),
        ...axisStyle(),
      },
      yAxis: {
        type: "value",
        axisLabel: {
          color: palette.inkSoft,
          formatter: "{value}s",
        },
        splitLine: {
          lineStyle: {
            color: palette.line,
          },
        },
      },
      series: [
        {
          type: "bar",
          barMaxWidth: 36,
          data: modalities.map((item) => Number(Number(item.avg_inference_time || 0).toFixed(3))),
          itemStyle: {
            color: palette.real,
          },
        },
      ],
    });
  }

  function initVerdictPieChart(el, verdictShare) {
    if (!el || !verdictShare?.length) {
      return null;
    }
    return buildChart(el, {
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(19, 38, 63, 0.92)",
        borderWidth: 0,
        textStyle: {
          color: "#eef6ff",
        },
        formatter: (params) => `${params.name}<br>数量：${params.value} (${params.percent}%)`,
      },
      series: [
        {
          type: "pie",
          radius: ["48%", "76%"],
          center: ["50%", "52%"],
          label: {
            color: palette.ink,
            formatter: "{b}\n{c}",
          },
          itemStyle: {
            borderWidth: 2,
            borderColor: "#ffffff",
          },
          data: verdictShare.map((item) => ({
            name: item.label === "fake" ? "Fake" : "Real",
            value: item.value,
            itemStyle: {
              color: item.label === "fake" ? palette.fake : palette.real,
            },
          })),
        },
      ],
    });
  }

  function initScoreHistogram(el, bins) {
    if (!el || !bins?.length) {
      return null;
    }
    return buildChart(el, {
      grid: baseGrid(),
      tooltip: tooltipStyle((params) => `${params[0].axisValue}<br>样本数：${params[0].value}`),
      xAxis: {
        type: "category",
        data: bins.map((item) => item.label),
        ...axisStyle(),
      },
      yAxis: {
        type: "value",
        ...axisStyle(),
      },
      series: [
        {
          type: "bar",
          barMaxWidth: 28,
          data: bins.map((item) => item.count),
          itemStyle: {
            color: palette.accent,
            borderRadius: [8, 8, 0, 0],
          },
        },
      ],
    });
  }

  function initTopRiskChart(el, samples) {
    if (!el || !samples?.length) {
      return null;
    }
    const reversed = [...samples].reverse();
    const maxScore = Math.max(1, ...reversed.map((item) => Number(item.score || 0)));
    return buildChart(el, {
      grid: baseGrid({ left: 8, right: 24 }),
      tooltip: tooltipStyle((params) => {
        const item = reversed[params[0].dataIndex];
        return [
          `<strong>${item.file_name}</strong>`,
          `风险分：${Number(item.score || 0).toFixed(3)}`,
          `结论：${item.label?.toUpperCase() || "-"}`,
          `耗时：${Number(item.inference_time || 0).toFixed(3)}s`,
        ].join("<br>");
      }),
      xAxis: {
        type: "value",
        min: 0,
        max: Number(maxScore.toFixed(2)),
        axisLabel: {
          color: palette.inkSoft,
        },
        splitLine: {
          lineStyle: {
            color: palette.line,
          },
        },
      },
      yAxis: {
        type: "category",
        data: reversed.map((item) => truncateLabel(item.file_name, 18)),
        axisLabel: {
          color: palette.inkSoft,
        },
        axisLine: {
          lineStyle: {
            color: palette.line,
          },
        },
      },
      series: [
        {
          type: "bar",
          data: reversed.map((item) => Number(Number(item.score || 0).toFixed(3))),
          barMaxWidth: 24,
          itemStyle: {
            color: palette.fake,
            borderRadius: [0, 8, 8, 0],
          },
        },
      ],
    });
  }

  window.DeepfakeViz = {
    initBatchTrendChart,
    initModeShareChart,
    initModeRiskChart,
    initModeLatencyChart,
    initVerdictPieChart,
    initScoreHistogram,
    initTopRiskChart,
    formatPercent,
    resolveModeLabel,
  };
})();
