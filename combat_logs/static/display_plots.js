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

var SMOOTHING_FACTOR = 10;  // seconds

var smooth = function(damage_stream, factor) {
  var base = damage_stream.start_time;
  var lead = 0, trail = 0;
  var stream = new Array((damage_stream.end_time - base) / 1000 + 1);
  var running_sum = 0;
  for (var i = 0; i < stream.length; i++) {
    while (lead < damage_stream.damage.length &&
           damage_stream.damage[lead][0] - base <= i * 1000) {
      running_sum += damage_stream.damage[lead][1];
      lead += 1;
    }
    while (trail < damage_stream.damage.length &&
           (damage_stream.damage[trail][0] - base)
           <= (i - SMOOTHING_FACTOR) * 1000) {
      running_sum -= damage_stream.damage[trail][1];
      trail += 1;
    }
    stream[i] = [base + i * 1000, running_sum / SMOOTHING_FACTOR];
  }
  return stream;
};

var make_label = function(damage_stream, enemy) {
  return (enemy
          + (damage_stream.ticker ? ' (' + damage_stream.ticker + ')' : '')
          + (damage_stream.weapon == 'Unknown'
             ? ''
             : ' ' + damage_stream.weapon)
          + ' [' + damage_stream.enemy_ships + ']');
};

var extract_plots = function(log_data, you_field, enemy_field) {
  var plots = [];
  $.each(log_data,
         function(idx, val) {
           if (val[you_field] == 'You') {
             plots.push({ label: make_label(val, val[enemy_field]),
                          data: smooth(val, SMOOTHING_FACTOR) });
           }
         });
  return plots;
};

var make_plot = function(selector, log_data, you_field, enemy_field, min, max) {
  $.plot($(selector), extract_plots(log_data, you_field, enemy_field),
         { xaxis: { mode: 'time',
                    min: min,
                    max: max
                  },
           yaxis: { min: 0 },
           legend: { position: 'nw' }
         });
};

var render = function(log_data) {
  var min = Math.min.apply(
    null,
    $.map(log_data, function (val) { return val.start_time; }));
  var max = Math.max.apply(
    null,
    $.map(log_data, function (val) { return val.end_time; }));
  make_plot('#attack', log_data, 'attacker', 'target', min, max);
  make_plot('#defense', log_data, 'target', 'attacker', min, max);
};

$(document).ready(
  function() {
    $('#upload_form').ajaxForm(
      {
        dataType: 'json',
        beforeSubmit: function() {
          $('#upload_status').html('Processing...');
        },
        success: function(data) {
          if (data.error) {
            $('#upload_status').html('<pre>' + data.error + '</pre>');
          } else {
            render(data);
            $('#upload_status').html('');
          }
        }
      });
  });
