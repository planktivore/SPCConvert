
// Create the new database
roistore = TAFFY([
{{#image_items}}
    {
        major_axis_length: {{maj_axis_len}},
        minor_axis_length: {{min_axis_len}},
        aspect_ratio: {{aspect_ratio}},
        area: {{area}},
        clipped_fraction: {{clipped_fraction}},
        orientation: {{orientation}},
        timestring: '{{timestring}}',
        timestamp: '{{timestamp}}',
        width: {{width}},
        height: {{height}},
        url: '{{url}}',

    },
{{/image_items}}
]);

