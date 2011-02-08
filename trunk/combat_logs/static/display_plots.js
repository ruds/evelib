// Copyright 2010 Matt Rudary
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//     http://www.apache.org/licenses/LICENSE-2.0
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

var SMOOTHING_FACTOR = 5;  // seconds -- half-width of smoothing

var smooth = function(damage_stream, factor) {
  var base = damage_stream.start_time;
  var lead = 0, trail = 0;
  var stream = new Array((damage_stream.end_time - base) / 1000 + 1);
  var running_sum = 0;
  for (var i = 0; i < stream.length; i++) {
    while (lead < damage_stream.damage.length &&
           damage_stream.damage[lead][0] - base
           <= (i + SMOOTHING_FACTOR) * 1000) {
      running_sum += damage_stream.damage[lead][1];
      lead += 1;
    }
    while (trail < damage_stream.damage.length &&
           damage_stream.damage[trail][0] - base
           <= (i - SMOOTHING_FACTOR) * 1000) {
      running_sum -= damage_stream.damage[trail][1];
      trail += 1;
    }
    stream[i] = [base + i * 1000, running_sum / (2 * SMOOTHING_FACTOR)];
  }
  return stream;
};

var make_label = function(damage_stream, enemy) {
  return (enemy
          + (damage_stream.ticker ? ' (' + damage_stream.ticker + ')' : '')
          + (damage_stream.weapon == 'Unknown'
             ? ''
             : ' ' + damage_stream.weapon)
          + ' ' + damage_stream.total_damage + 'dmg'
          + ' [' + damage_stream.enemy_ships + ']');
};

var extract_plots = function(log_data, you_field, enemy_field, min, max) {
  var plots = [];
  $.each(log_data,
         function(idx, val) {
           if (val.start_time <= max
               && val.end_time >= min
               && val[you_field] == 'You') {
             plots.push({ label: make_label(val, val[enemy_field]),
                          data: smooth(val, SMOOTHING_FACTOR) });
           }
         });
  return plots;
};

var date_string = function(time_msec) {
  var d = new Date(time_msec);
  return ([d.getUTCFullYear(), d.getUTCMonth() + 1, d.getUTCDate()].join('/')
          + ' '
          + [d.getUTCHours(), d.getUTCMinutes(), d.getUTCSeconds()].join(':'));
};

var make_csv = function(log_data) {
  var row = ['time'];
  $.each(log_data,
         function(idx, val) {
           if (val.target == 'You') {
             row.push('"attacker: ' + make_label(val, val.attacker) + '"');
           } else {
             row.push('"target: ' + make_label(val, val.target) + '"');
           }
         });
  var all_rows = [row.join(',')];

  // iterators into each of the lists
  var idx = new Array(log_data.length);
  // the current timestamp in each of the lists
  var cur = new Array(log_data.length);
  $.each(log_data, function (i) { idx[i] = 0;
                                  cur[i] = log_data[i].damage[0][0];});
  // the working timestamp
  var working = Math.min.apply(null, cur);
  while (isFinite(working)) {
    row = [date_string(working)];
    $.each(log_data,
           function(i, val) {
             if (idx[i] < val.damage.length) {
               if (val.damage[idx[i]][0] == working) {
                 row.push(val.damage[idx[i]][1]);
                 idx[i] += 1;
                 if (idx[i] < val.damage.length) {
                   cur[i] = val.damage[idx[i]][0];
                 } else {
                   cur[i] = Number.POSITIVE_INFINITY;
                 }
               } else {
                 row.push('');
               }
             } else {
               row.push('');
             }
           });
    all_rows.push(row.join(','));
    working = Math.min.apply(null, cur);
  }
  return all_rows.join('\n');
};

var make_plot = function(selector, log_data, you_field, enemy_field,
                         min, max, show_legend) {
  $.plot($(selector), extract_plots(log_data, you_field, enemy_field, min, max),
         { xaxis: { mode: 'time',
                    min: min,
                    max: max
                  },
           yaxis: { min: 0 },
           selection: { mode: "x" },
           legend: { position: 'nw',
                     show: show_legend
                   }
         });
};

var render = function() {
  var show_legend = $('#show_legend:checked').val() == 'show';
  make_plot('#attack', log_data, 'attacker', 'target', min, max, show_legend);
  make_plot('#defense', log_data, 'target', 'attacker', min, max, show_legend);
};

var handle_selection = function(event, ranges) {
  min = ranges.xaxis.from;
  max = ranges.xaxis.to;
  $('#zoom_out_button').attr('disabled', '');
  render();
};

var reset_boundaries = function() {
  $('#zoom_out_button').attr('disabled', 'disabled');
  min = Math.min.apply(
    null,
    $.map(log_data, function (val) { return val.start_time; }));
  max = Math.max.apply(
    null,
    $.map(log_data, function (val) { return val.end_time; }));
};

var log_data = [];
var min = 0;
var max = Infinity;

$(document).ready(
  function() {
    $('#upload_form').ajaxForm(
      {
        dataType: 'json',
        beforeSubmit: function() {
          $('#upload_status').html('Processing...');
        },
        success: function(data) {
          var $out = $('#upload_status');
          if (data.error) {
            $out.html('<pre>' + data.error + '</pre>');
          } else {
            $('#your_dps_h1').html(data.Your + ' DPS');
            log_data = data.arr;
            reset_boundaries();
            render();
            $out.html('');
            $('#download_form').css('visibility', 'visible');
          }
        }
      });
    $('#upload_form').css('visibility', 'visible');
    $('#show_legend').change(function() { render(); });
    $('#zoom_out_button').click(function() { reset_boundaries(); render(); });
    $('#zoom_out_button').attr('disabled', 'disabled');
    $('.graphblock > div').bind('plotselected', handle_selection);
    $(window).resize(function() { render(); });
    $('#download_button').click(
      function() {
        $("#download_content").val(make_csv(log_data));
        $('#download_form').submit();
      });
  });
